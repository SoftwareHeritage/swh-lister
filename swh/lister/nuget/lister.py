# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging
from typing import Dict, Iterator, List, Optional

from bs4 import BeautifulSoup
from requests.exceptions import HTTPError

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, StatelessLister

logger = logging.getLogger(__name__)

# Aliasing the page results returned by `get_pages` method from the lister.
NugetListerPage = List[Dict[str, str]]


class NugetLister(StatelessLister[NugetListerPage]):
    """List Nuget (Package manager for .NET) origins."""

    LISTER_NAME = "nuget"
    INSTANCE = "nuget"

    API_INDEX_URL = "https://api.nuget.org/v3/catalog0/index.json"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        credentials: Optional[CredentialsType] = None,
    ):
        super().__init__(
            scheduler=scheduler,
            credentials=credentials,
            instance=self.INSTANCE,
            url=self.API_INDEX_URL,
        )

    def get_pages(self) -> Iterator[NugetListerPage]:
        """Yield an iterator which returns 'page'

        It uses the following endpoint `https://api.nuget.org/v3/catalog0/index.json`
        to get a list of pages endpoint to iterate.
        """
        index_response = self.http_request(url=self.url)
        index = index_response.json()
        assert "items" in index

        for page in index["items"]:
            assert page["@id"]
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
            repo = xml.find("repository")
            if repo and "url" in repo.attrs and "type" in repo.attrs:
                vcs_url = repo.attrs["url"]
                vcs_type = repo.attrs["type"]
                yield ListedOrigin(
                    lister_id=self.lister_obj.id,
                    visit_type=vcs_type,
                    url=vcs_url,
                    last_update=None,
                )
            else:
                continue
