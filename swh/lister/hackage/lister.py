# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging
from typing import Any, Dict, Iterator, List, Optional

import iso8601

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, StatelessLister

logger = logging.getLogger(__name__)

# Aliasing the page results returned by `get_pages` method from the lister.
HackageListerPage = List[Dict[str, Any]]


class HackageLister(StatelessLister[HackageListerPage]):
    """List Hackage (The Haskell Package Repository) origins."""

    LISTER_NAME = "hackage"
    VISIT_TYPE = "hackage"
    INSTANCE = "hackage"

    BASE_URL = "https://hackage.haskell.org/"
    PACKAGE_NAMES_URL_PATTERN = "{base_url}packages/search"
    PACKAGE_INFO_URL_PATTERN = "{base_url}package/{pkgname}"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        credentials: Optional[CredentialsType] = None,
        url: Optional[str] = None,
    ):
        super().__init__(
            scheduler=scheduler,
            credentials=credentials,
            instance=self.INSTANCE,
            url=url if url else self.BASE_URL,
        )
        # Ensure to set this with same value as the http api search endpoint use
        # (50 as of august 2022)
        self.page_size: int = 50

    def get_pages(self) -> Iterator[HackageListerPage]:
        """Yield an iterator which returns 'page'

        It uses the http api endpoint `https://hackage.haskell.org/packages/search`
        to get a list of package names from which we build an origin url.

        Results are paginated.
        """
        params = {
            "page": 0,
            "sortColumn": "default",
            "sortDirection": "ascending",
            "searchQuery": "(deprecated:any)",
        }

        data = self.http_request(
            url=self.PACKAGE_NAMES_URL_PATTERN.format(base_url=self.url),
            method="POST",
            json=params,
        ).json()

        nb_entries: int = data["numberOfResults"]
        (nb_pages, remainder) = divmod(nb_entries, self.page_size)
        if remainder:
            nb_pages += 1
        yield data["pageContents"]

        for page in range(1, nb_pages):
            params["page"] = page
            data = self.http_request(
                url=self.PACKAGE_NAMES_URL_PATTERN.format(base_url=self.url),
                method="POST",
                json=params,
            ).json()
            yield data["pageContents"]

    def get_origins_from_page(self, page: HackageListerPage) -> Iterator[ListedOrigin]:
        """Iterate on all pages and yield ListedOrigin instances."""
        assert self.lister_obj.id is not None

        for entry in page:
            pkgname = entry["name"]["display"]
            last_update = iso8601.parse_date(entry["lastUpload"])
            url = self.PACKAGE_INFO_URL_PATTERN.format(
                base_url=self.url, pkgname=pkgname
            )
            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                visit_type=self.VISIT_TYPE,
                url=url,
                last_update=last_update,
            )
