# Copyright (C) 2022-2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any, Dict, Iterator, List, Optional

from bs4 import BeautifulSoup
import iso8601
from requests.exceptions import HTTPError

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, Lister

logger = logging.getLogger(__name__)


# Aliasing the page results returned by `get_pages` method from the lister.
NugetListerPage = List[Dict[str, str]]


@dataclass
class NugetListerState:
    """Store lister state for incremental mode operations"""

    last_listing_date: Optional[datetime] = None
    """Last date from main http api endpoint when lister was executed"""


class NugetLister(Lister[NugetListerState, NugetListerPage]):
    """List Nuget (Package manager for .NET) origins."""

    LISTER_NAME = "nuget"
    INSTANCE = "nuget"

    API_INDEX_URL = "https://api.nuget.org/v3/catalog0/index.json"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: str = API_INDEX_URL,
        instance: str = INSTANCE,
        credentials: Optional[CredentialsType] = None,
        max_origins_per_page: Optional[int] = None,
        max_pages: Optional[int] = None,
        enable_origins: bool = True,
    ):
        super().__init__(
            scheduler=scheduler,
            credentials=credentials,
            instance=instance,
            url=url,
            max_origins_per_page=max_origins_per_page,
            max_pages=max_pages,
            enable_origins=enable_origins,
        )
        self.listing_date: Optional[datetime] = None

    def state_from_dict(self, d: Dict[str, Any]) -> NugetListerState:
        last_listing_date = d.get("last_listing_date")
        if last_listing_date is not None:
            d["last_listing_date"] = iso8601.parse_date(last_listing_date)
        return NugetListerState(**d)

    def state_to_dict(self, state: NugetListerState) -> Dict[str, Any]:
        d: Dict[str, Optional[str]] = {"last_listing_date": None}
        last_listing_date = state.last_listing_date
        if last_listing_date is not None:
            d["last_listing_date"] = last_listing_date.isoformat()
        return d

    def get_pages(self) -> Iterator[NugetListerPage]:
        """Yield an iterator which returns 'page'

        It uses the following endpoint `https://api.nuget.org/v3/catalog0/index.json`
        to get a list of pages endpoint to iterate.
        """
        index_response = self.http_request(url=self.url)
        index = index_response.json()

        assert "commitTimeStamp" in index
        self.listing_date = iso8601.parse_date(index["commitTimeStamp"])

        assert "items" in index
        for page in index["items"]:
            assert page["@id"]
            assert page["commitTimeStamp"]

            commit_timestamp = iso8601.parse_date(page["commitTimeStamp"])

            if (
                not self.state.last_listing_date
                or commit_timestamp > self.state.last_listing_date
            ):
                try:
                    page_response = self.http_request(url=page["@id"])
                    page_data = page_response.json()
                    assert "items" in page_data
                    yield page_data["items"]
                except HTTPError:
                    logger.warning(
                        "Failed to fetch page %s, skipping it from listing.",
                        page["@id"],
                    )
                    continue

    def get_origins_from_page(self, page: NugetListerPage) -> Iterator[ListedOrigin]:
        """Iterate on all pages and yield ListedOrigin instances.
        .NET packages are binary, dll, etc. We retrieve only packages for which we can
        find a vcs repository.

        To check if a vcs repository exists, we need for each entry in a page to retrieve
        a .nuspec file, which is a package metadata xml file, and search for a `repository`
        value.
        """
        assert self.lister_obj.id is not None

        for elt in page:
            try:
                res = self.http_request(url=elt["@id"])
            except HTTPError:
                logger.warning(
                    "Failed to fetch page %s, skipping it from listing.",
                    elt["@id"],
                )
                continue

            data = res.json()
            pkgname = data["id"]
            nuspec_url = (
                f"https://api.nuget.org/v3-flatcontainer/{pkgname.lower()}/"
                f"{data['version'].lower()}/{pkgname.lower()}.nuspec"
            )

            try:
                res_metadata = self.http_request(url=nuspec_url)
            except HTTPError:
                logger.warning(
                    "Failed to fetch nuspec file %s, skipping it from listing.",
                    nuspec_url,
                )
                continue
            xml = BeautifulSoup(res_metadata.content, "xml")
            repo = xml.select_one("repository")
            if repo and "url" in repo.attrs and "type" in repo.attrs:
                vcs_url = repo.attrs["url"]
                vcs_type = repo.attrs["type"]
                last_update = iso8601.parse_date(elt["commitTimeStamp"])
                yield ListedOrigin(
                    lister_id=self.lister_obj.id,
                    visit_type=vcs_type,
                    url=vcs_url,
                    last_update=last_update,
                )
            else:
                continue

    def finalize(self) -> None:
        self.state.last_listing_date = self.listing_date
        self.updated = True
