# Copyright (C) 2023 The Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from datetime import datetime, timezone
import logging
import re
from typing import Any, Dict, Iterator, List, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from requests.exceptions import HTTPError

from swh.lister.pattern import CredentialsType, StatelessLister
from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

logger = logging.getLogger(__name__)

Repositories = List[Dict[str, Any]]


class StagitLister(StatelessLister[Repositories]):
    """Lister class for Stagit forge instances.

    This lister will retrieve the list of published git repositories by
    parsing the HTML page(s) of the index retrieved at `url`.

    """

    LISTER_NAME = "stagit"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: Optional[str] = None,
        instance: Optional[str] = None,
        credentials: Optional[CredentialsType] = None,
        max_origins_per_page: Optional[int] = None,
        max_pages: Optional[int] = None,
        enable_origins: bool = True,
    ):
        """Lister class for Stagit repositories.

        Args:
            url: (Optional) Root URL of the Stagit instance, i.e. url of the index of
                published git repositories on this instance. Defaults to
                :file:`https://{instance}` if unset.
            instance: Name of stagit instance. Defaults to url's network location
                if unset.

        """
        super().__init__(
            scheduler=scheduler,
            url=url,
            instance=instance,
            credentials=credentials,
            max_origins_per_page=max_origins_per_page,
            max_pages=max_pages,
            enable_origins=enable_origins,
        )

        self.session.headers.update({"Accept": "application/html"})

    def _get_and_parse(self, url: str) -> BeautifulSoup:
        """Get the given url and parse the retrieved HTML using BeautifulSoup"""
        response = self.http_request(url)
        return BeautifulSoup(response.text, features="html.parser")

    def get_pages(self) -> Iterator[Repositories]:
        """Generate git 'project' URLs found on the current Stagit server."""
        bs_idx = self._get_and_parse(self.url)

        page_results = []

        for tr in bs_idx.find("table", {"id": re.compile("index")}).find_all("tr"):
            link = tr.find("a")
            if not link:
                continue

            repo_description_url = self.url + "/" + link["href"]

            # This retrieves the date in format "%Y-%m-%d %H:%M"
            tds = tr.find_all("td")
            last_update = tds[-1].text if tds and tds[-1] else None

            page_results.append(
                {"url": repo_description_url, "last_update": last_update}
            )

        yield page_results

    def get_origins_from_page(
        self, repositories: Repositories
    ) -> Iterator[ListedOrigin]:
        """Convert a page of stagit repositories into a list of ListedOrigins."""
        assert self.lister_obj.id is not None

        for repo in repositories:
            origin_url = self._get_origin_from_repository_url(repo["url"])
            if origin_url is None:
                continue

            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                url=origin_url,
                visit_type="git",
                last_update=_parse_date(repo["last_update"]),
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

        urls = [
            td.find("a")["href"]
            for row in bs.find_all("tr", {"class": "url"})
            for td in row.find_all("td")
            if td.text.startswith("git clone")
        ]

        if not urls:
            return None

        urls = [url for url in urls if urlparse(url).scheme in ("https", "http", "git")]
        if not urls:
            return None
        return urls[0]


def _parse_date(date: Optional[str]) -> Optional[datetime]:
    """Parse the last update date."""
    if not date:
        return None

    parsed_date = None
    try:
        parsed_date = datetime.strptime(date, "%Y-%m-%d %H:%M").replace(
            tzinfo=timezone.utc
        )
    except Exception:
        logger.warning(
            "Could not parse last_update date: %s",
            date,
        )

    return parsed_date
