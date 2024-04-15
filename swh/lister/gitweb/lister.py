# Copyright (C) 2023-2024 The Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from datetime import datetime, timezone
import logging
from typing import Any, Dict, Iterator, List, Optional
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup
from dateparser import parse
from requests.exceptions import HTTPError

from swh.lister.pattern import CredentialsType, StatelessLister
from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

logger = logging.getLogger(__name__)

Repositories = List[Dict[str, Any]]


class GitwebLister(StatelessLister[Repositories]):
    """Lister class for Gitweb repositories.

    This lister will retrieve the list of published git repositories by
    parsing the HTML page(s) of the index retrieved at `url`.

    """

    LISTER_NAME = "gitweb"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: Optional[str] = None,
        instance: Optional[str] = None,
        base_git_url: Optional[str] = None,
        credentials: Optional[CredentialsType] = None,
        max_origins_per_page: Optional[int] = None,
        max_pages: Optional[int] = None,
        enable_origins: bool = True,
    ):
        """Lister class for Gitweb repositories.

        Args:
            url: Root URL of the Gitweb instance, i.e. url of the index of
                published git repositories on this instance. Defaults to
                :file:`https://{instance}` if unset.
            instance: Name of gitweb instance. Defaults to url's network location
                if unset.
            base_git_url: Base URL to clone a git project hosted on the Gitweb instance,
                should only be used if the clone URLs cannot be found when scraping project
                page or cannot be easily derived from the root URL of the instance

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
        self.instance_scheme = urlparse(url).scheme
        self.base_git_url = base_git_url

    def _get_and_parse(self, url: str) -> BeautifulSoup:
        """Get the given url and parse the retrieved HTML using BeautifulSoup"""
        response = self.http_request(url)
        return BeautifulSoup(response.text, features="html.parser")

    def get_pages(self) -> Iterator[Repositories]:
        """Generate git 'project' URLs found on the current Gitweb server."""
        bs_idx = self._get_and_parse(self.url)

        page_results = []

        for tr in bs_idx.select("table.project_list tr"):
            link = tr.select_one("a")
            if not link:
                continue

            repo_url = urljoin(self.url, link.attrs["href"]).strip("/")

            # Skip this description page which is listed but won't yield any origins to list
            if repo_url.endswith("?o=descr"):
                continue

            # This retrieves the date interval in natural language (e.g. '9 years ago')
            # to actual python datetime interval so we can derive last update
            span = tr.select_one('td[class^="age"]')
            page_results.append(
                {"url": repo_url, "last_update_interval": span.text if span else None}
            )

        yield page_results

    def get_origins_from_page(
        self, repositories: Repositories
    ) -> Iterator[ListedOrigin]:
        """Convert a page of gitweb repositories into a list of ListedOrigins."""
        assert self.lister_obj.id is not None

        for repo in repositories:
            origin_url = self._get_origin_from_repository_url(repo["url"])
            if origin_url is None:
                continue

            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                url=origin_url,
                visit_type="git",
                last_update=parse_last_update(repo.get("last_update_interval")),
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

        urls = []
        for row in bs.select("tr.metadata_url"):
            url = row.select("td")[-1].text.strip()
            for scheme in ("http", "https", "git"):
                # remove any string prefix before origin
                pos = url.find(f"{scheme}://")
                if pos != -1:
                    url = url[pos:]
                    break

            if "," in url:
                urls_ = [s.strip() for s in url.split(",") if s]
                urls.extend(urls_)
            else:
                urls.append(url)

        if not urls:
            repo = try_to_determine_git_repository(repository_url, self.base_git_url)
            if not repo:
                logger.debug("No git urls found on %s", repository_url)
            return repo

        # look for the http/https url, if any, and use it as origin_url
        for url in urls:
            parsed_url = urlparse(url)
            if parsed_url.scheme == "https":
                origin_url = url
                break
            elif parsed_url.scheme == "http" and self.instance_scheme == "https":
                # workaround for non-working listed http origins
                origin_url = url.replace("http://", "https://")
                break
        else:
            # otherwise, choose the first one
            origin_url = urls[0]
        return origin_url


def try_to_determine_git_repository(
    repository_url: str, base_git_url: Optional[str] = None
) -> Optional[str]:
    """Some gitweb instances does not advertise the git urls.

    This heuristic works on instances demonstrating this behavior.

    """
    result = None
    parsed_url = urlparse(repository_url)
    repo = parse_qs(parsed_url.query, separator=";").get("p")
    if repo:
        if base_git_url:
            result = f"{base_git_url.rstrip('/')}/{repo[0]}"
        else:
            result = f"git://{parsed_url.netloc}/{repo[0]}"
    return result


def parse_last_update(last_update_interval: Optional[str]) -> Optional[datetime]:
    """Parse the last update string into a datetime."""
    if not last_update_interval:
        return None
    last_update_date = parse(last_update_interval)
    last_update = None
    if last_update_date is not None:
        last_update = last_update_date.replace(tzinfo=timezone.utc)
    return last_update
