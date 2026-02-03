# Copyright (C) 2026  The Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Iterator, List, Optional, Tuple
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

from bs4 import BeautifulSoup
from requests.exceptions import HTTPError, JSONDecodeError

from swh.lister.pattern import CredentialsType, StatelessLister
from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

Repositories = List[Tuple[str, Optional[datetime]]]


class HgwebLister(StatelessLister[Repositories]):
    """Lister class for Hgweb repositories.

    This lister uses the hgweb json template style if it works and
    if the url value is available in the JSON response.

    https://repo.mercurial-scm.org/hg/help/hgweb

    This lister falls back on parsing the HTML if it doesn't.
    """

    LISTER_NAME = "hgweb"

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
        enable_api: bool = True,
    ):
        """Lister class for Hgweb repositories."""
        super().__init__(
            scheduler=scheduler,
            url=url,
            instance=instance,
            credentials=credentials,
            max_origins_per_page=max_origins_per_page,
            max_pages=max_pages,
            enable_origins=enable_origins,
        )

        self.enable_api = enable_api

    def _api_url(self, url):
        api_url = urlparse(url)
        params = parse_qs(api_url.query)
        params["style"] = ["json"]
        query = urlencode(params, doseq=True)
        api_url = api_url._replace(query=query)
        return api_url.geturl()

    def _get_json_pages(self) -> Iterator[Repositories]:
        # This will only work once this patch has been released:
        # https://foss.heptapod.net/mercurial/mercurial-devel/-/merge_requests/1822
        if not self.enable_api:
            raise ValueError("The use of the JSON API is not enabled")
        hostname = urlparse(self.url).hostname
        if hostname and hostname.endswith(".mozilla.org"):
            raise ValueError("The Mozilla hgweb JSON style is missing directories")
        self.session.headers.update({"Accept": "application/json"})
        done: set[str] = set()
        todo = {self.url}
        while todo:
            url = todo.pop()
            done.add(url)
            api_url = self._api_url(url)
            response = self.http_request(api_url)
            response.raise_for_status()
            data = response.json()
            entries = data.get("entries", [])
            if not entries:
                raise ValueError("No entries in JSON")
            page_results = []
            for entry in entries:
                if url := entry.get("url"):
                    url = urljoin(self.url, url)
                    name = entry.get("name", "")
                    # when isdirectory is not yet present, fallback on
                    # that directory names have a trailing / character
                    # https://foss.heptapod.net/mercurial/mercurial-devel/-/blob/branch/default/mercurial/hgweb/hgwebdir_mod_inner.py#L177
                    if entry.get("isdirectory", name.endswith("/")):
                        # directories
                        if url not in done:
                            todo.add(url)
                    else:
                        # repositories
                        lastchange = next(iter(entry.get("lastchange", [])), None)
                        if lastchange is not None:
                            lastchange = datetime.fromtimestamp(
                                lastchange, tz=timezone.utc
                            )
                        page_results.append((url, lastchange))
                else:
                    raise ValueError("No URLs in JSON entries")
            yield page_results

    def _get_html_pages(self) -> Iterator[Repositories]:
        """Get the given url and parse the retrieved HTML using BeautifulSoup"""
        self.session.headers.update({"Accept": "application/html"})
        done: set[str] = set()
        todo = {self.url}
        while todo:
            url = todo.pop()
            done.add(url)
            response = self.http_request(url)
            response.raise_for_status()
            doc = BeautifulSoup(response.text, features="html.parser")
            page_results = []
            for tr in doc.select("table tr"):
                tds = tr.select("td")
                if tds and len(tds) >= 4:
                    # mainline hgweb row for a repository or a directory
                    link = tr.select_one("a")
                    if not link:
                        continue
                    href = link.attrs["href"]
                    if href.startswith("?sort="):
                        # skip headers
                        continue
                    url = urljoin(self.url, href)
                    # the hgweb gitweb template style has extra whitespace
                    name = link.text.rstrip()
                    # directory names have a trailing / character
                    # https://foss.heptapod.net/mercurial/mercurial-devel/-/blob/branch/default/mercurial/hgweb/hgwebdir_mod_inner.py#L177
                    if name.endswith("/"):
                        # directories
                        if url not in done:
                            todo.add(url)
                    else:
                        # repositories
                        age = tr.select_one('td[class="age"]')
                        # remove Mozilla timestamp prefix
                        # https://hg-edge.mozilla.org/hgcustom/version-control-tools/file/tip/hgtemplates/gitweb_mozilla/map#l336
                        age_text = age.text.strip().removeprefix("at ") if age else None
                        try:
                            # Default templates use RFC 822 dates
                            # https://foss.heptapod.net/mercurial/mercurial-devel/-/blob/branch/default/mercurial/templates/monoblue/map#L288
                            lastchange = parsedate_to_datetime(age_text)
                        except ValueError:
                            try:
                                # Mozilla templates use RFC 3339 dates
                                # https://hg-edge.mozilla.org/hgcustom/version-control-tools/file/tip/hgtemplates/gitweb_mozilla/map#l336
                                lastchange = datetime.fromisoformat(age_text or "")
                            except ValueError:
                                lastchange = None
                        page_results.append((url, lastchange))
                elif tds:
                    # Mozilla hgweb index row for a directory
                    # https://hg-edge.mozilla.org/hgcustom/version-control-tools/file/tip/hgtemplates/.patches/index.patch
                    link = tr.select_one("a")
                    if not link:
                        continue
                    href = link.attrs["href"]
                    url = urljoin(self.url, href)
                    if url not in done:
                        todo.add(url)
            yield page_results

    def get_pages(self) -> Iterator[Repositories]:
        """Generate hg "project" URLs found on the current Hgweb server."""
        try:
            yield from self._get_json_pages()
        except (ValueError, HTTPError, JSONDecodeError):
            yield from self._get_html_pages()

    def get_origins_from_page(
        self, repositories: Repositories
    ) -> Iterator[ListedOrigin]:
        """Convert a page of hgweb repositories into a list of ListedOrigins."""
        assert self.lister_obj.id is not None

        for origin_url, last_update in repositories:
            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                url=origin_url,
                visit_type="hg",
                last_update=last_update,
            )
