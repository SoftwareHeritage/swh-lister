# Copyright (C) 2019-2021 The Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from datetime import datetime, timezone
import logging
import re
from typing import Any, Dict, Iterator, List, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
import requests
from requests.exceptions import HTTPError

from swh.lister import USER_AGENT
from swh.lister.pattern import StatelessLister
from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

logger = logging.getLogger(__name__)

Repositories = List[Dict[str, Any]]


class CGitLister(StatelessLister[Repositories]):
    """Lister class for CGit repositories.

    This lister will retrieve the list of published git repositories by
    parsing the HTML page(s) of the index retrieved at `url`.

    For each found git repository, a query is made at the given url found
    in this index to gather published "Clone" URLs to be used as origin
    URL for that git repo.

    If several "Clone" urls are provided, prefer the http/https one, if
    any, otherwise fallback to the first one.
    """

    LISTER_NAME = "cgit"

    def __init__(
        self, scheduler: SchedulerInterface, url: str, instance: Optional[str] = None
    ):
        """Lister class for CGit repositories.

        Args:
            url (str): main URL of the CGit instance, i.e. url of the index
                of published git repositories on this instance.
            instance (str): Name of cgit instance. Defaults to url's hostname
                if unset.

        """
        if not instance:
            instance = urlparse(url).hostname
        assert instance is not None  # Make mypy happy

        super().__init__(
            scheduler=scheduler, credentials=None, url=url, instance=instance,
        )

        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/html", "User-Agent": USER_AGENT}
        )

    def _get_and_parse(self, url: str) -> BeautifulSoup:
        """Get the given url and parse the retrieved HTML using BeautifulSoup"""
        response = self.session.get(url)
        response.raise_for_status()
        return BeautifulSoup(response.text, features="html.parser")

    def get_pages(self) -> Iterator[Repositories]:
        """Generate git 'project' URLs found on the current CGit server
            The last_update date is retrieved on the list of repo page to avoid
            to compute it on the repository details which only give a date per branch
        """
        next_page: Optional[str] = self.url
        while next_page:
            bs_idx = self._get_and_parse(next_page)

            page_results = []

            for tr in bs_idx.find("div", {"class": "content"}).find_all(
                "tr", {"class": ""}
            ):
                url = urljoin(self.url, tr.find("a")["href"])
                span = tr.find("span", {"class": re.compile("age-")})
                if span:
                    last_updated_date = span["title"]
                else:
                    last_updated_date = None

                page_results.append(
                    {"url": url, "last_updated_date": last_updated_date}
                )

            yield page_results

            try:
                pager = bs_idx.find("ul", {"class": "pager"})

                current_page = pager.find("a", {"class": "current"})
                if current_page:
                    next_page = current_page.parent.next_sibling.a["href"]
                    next_page = urljoin(self.url, next_page)
            except (AttributeError, KeyError):
                # no pager, or no next page
                next_page = None

    def get_origins_from_page(
        self, repositories: Repositories
    ) -> Iterator[ListedOrigin]:
        """Convert a page of cgit repositories into a list of ListedOrigins."""
        assert self.lister_obj.id is not None

        for repository in repositories:
            origin_url = self._get_origin_from_repository_url(repository["url"])
            if origin_url is None:
                continue

            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                url=origin_url,
                visit_type="git",
                last_update=_parse_last_updated_date(repository),
            )

    def _get_origin_from_repository_url(self, repository_url: str) -> Optional[str]:
        """Extract the git url from the repository page"""
        try:
            bs = self._get_and_parse(repository_url)
        except HTTPError as e:
            logger.warning(
                "Unexpected HTTP status code %s on %s",
                e.response.status_code,
                e.response.url,
            )
            return None

        # origin urls are listed on the repository page
        # TODO check if forcing https is better or not ?
        # <link rel='vcs-git' href='git://...' title='...'/>
        # <link rel='vcs-git' href='http://...' title='...'/>
        # <link rel='vcs-git' href='https://...' title='...'/>
        urls = [x["href"] for x in bs.find_all("a", {"rel": "vcs-git"})]

        if not urls:
            return None

        # look for the http/https url, if any, and use it as origin_url
        for url in urls:
            if urlparse(url).scheme in ("http", "https"):
                origin_url = url
                break
        else:
            # otherwise, choose the first one
            origin_url = urls[0]
        return origin_url


def _parse_last_updated_date(repository: Dict[str, Any]) -> Optional[datetime]:
    """Parse the last updated date"""
    date = repository.get("last_updated_date")
    if not date:
        return None

    parsed_date = None
    for date_format in ("%Y-%m-%d %H:%M:%S %z", "%Y-%m-%d %H:%M:%S (%Z)"):
        try:
            parsed_date = datetime.strptime(date, date_format)
            # force UTC to avoid naive datetime
            if not parsed_date.tzinfo:
                parsed_date = parsed_date.replace(tzinfo=timezone.utc)
            break
        except Exception:
            pass

    if not parsed_date:
        logger.warning(
            "Could not parse %s last_updated date: %s", repository["url"], date,
        )

    return parsed_date
