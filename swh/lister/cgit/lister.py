# Copyright (C) 2019-2024 The Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from datetime import datetime, timezone
import logging
from typing import Any, Dict, Iterator, List, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from requests.exceptions import HTTPError

from swh.lister.pattern import CredentialsType, StatelessLister
from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

logger = logging.getLogger(__name__)

Repositories = List[Dict[str, Any]]


class CGitLister(StatelessLister[Repositories]):
    """Lister class for CGit repositories.

    This lister will retrieve the list of published git repositories by
    parsing the HTML page(s) of the index retrieved at `url`.

    The lister currently defines 2 listing behaviors:

    - If the `base_git_url` is provided, the listed origin urls are computed out of the
      base git url link and the one listed in the main listed page (resulting in less
      HTTP queries than the 2nd behavior below). This is expected to be the main
      deployed behavior.

    - Otherwise (with no `base_git_url`), for each found git repository listed, one
      extra HTTP query is made at the given url found in the main listing page to gather
      published "Clone" URLs to be used as origin URL for that git repo. If several
      "Clone" urls are provided, prefer the http/https one, if any, otherwise fallback
      to the first one.

    """

    LISTER_NAME = "cgit"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: Optional[str] = None,
        instance: Optional[str] = None,
        credentials: Optional[CredentialsType] = None,
        base_git_url: Optional[str] = None,
        max_origins_per_page: Optional[int] = None,
        max_pages: Optional[int] = None,
        enable_origins: bool = True,
    ):
        """Lister class for CGit repositories.

        Args:
            url: (Optional) Root URL of the CGit instance, i.e. url of the index of
                published git repositories on this instance. Defaults to
                :file:`https://{instance}` if unset.
            instance: Name of cgit instance. Defaults to url's network location
                if unset.
            base_git_url: Optional base git url which allows the origin url
                computations.

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
        self.base_git_url = base_git_url

    def _get_and_parse(self, url: str) -> BeautifulSoup:
        """Get the given url and parse the retrieved HTML using BeautifulSoup"""
        response = self.http_request(url)
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

            for tr in bs_idx.select("div.content tr:not([class])"):
                repository_link = tr.select_one("a")

                if repository_link is None:
                    continue

                repo_url = None
                git_url = None

                base_url = urljoin(self.url, repository_link.attrs["href"]).strip("/")
                if self.base_git_url:  # mapping provided
                    # computing git url
                    git_url = base_url.replace(self.url, self.base_git_url)
                else:
                    # we compute the git detailed page url from which we will retrieve
                    # the git url (cf. self.get_origins_from_page)
                    repo_url = base_url

                span = tr.select_one('span[class^="age-"]')
                last_updated_date = span.get("title") if span else None

                page_results.append(
                    {
                        "url": repo_url,
                        "git_url": git_url,
                        "last_updated_date": last_updated_date,
                    }
                )

            yield page_results

            try:
                next_page_li = bs_idx.select_one(
                    "ul.pager li:has(> a.current) + li:has(> a)"
                )
                next_page = (
                    urljoin(self.url, next_page_li.select("a")[0].attrs["href"])
                    if next_page_li
                    else None
                )
            except (AttributeError, KeyError):
                # no pager, or no next page
                next_page = None

    def get_origins_from_page(
        self, repositories: Repositories
    ) -> Iterator[ListedOrigin]:
        """Convert a page of cgit repositories into a list of ListedOrigins."""
        assert self.lister_obj.id is not None

        for repo in repositories:
            origin_url = repo["git_url"] or self._get_origin_from_repository_url(
                repo["url"]
            )
            if origin_url is None:
                continue

            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                url=origin_url,
                visit_type="git",
                last_update=_parse_last_updated_date(repo),
            )

    def _get_origin_from_repository_url(self, repository_url: str) -> Optional[str]:
        """Extract the git url from the repository page"""
        try:
            bs = self._get_and_parse(repository_url)
        except HTTPError as e:
            assert e.response is not None
            logger.warning(
                "Unexpected HTTP status code %s on %s",
                e.response.status_code,
                e.response.url,
            )
            return None

        # check if we are on the summary tab, if not, go to this tab
        summary_a = bs.select_one('table.tabs a:-soup-contains("summary")')
        if summary_a:
            summary_path = summary_a.attrs["href"]
            summary_url = urljoin(repository_url, summary_path).strip("/")

            if summary_url != repository_url:
                logger.debug(
                    "%s : Active tab is not the summary, trying to load the summary page",
                    repository_url,
                )
                return self._get_origin_from_repository_url(summary_url)
        else:
            logger.debug("No summary tab found on %s", repository_url)

        # origin urls are listed on the repository page
        # TODO check if forcing https is better or not ?
        # <link rel='vcs-git' href='git://...' title='...'/>
        # <link rel='vcs-git' href='http://...' title='...'/>
        # <link rel='vcs-git' href='https://...' title='...'/>
        urls = [x.attrs["href"] for x in bs.select('a[rel="vcs-git"]')]

        if not urls:
            logger.debug("No git urls found on %s", repository_url)
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
            "Could not parse %s last_updated date: %s",
            repository["url"],
            date,
        )

    return parsed_date
