# Copyright (C) 2022-2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Any, Dict, Iterator, List, Optional

import iso8601

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, Lister

logger = logging.getLogger(__name__)

# Aliasing the page results returned by `get_pages` method from the lister.
HackageListerPage = List[Dict[str, Any]]


@dataclass
class HackageListerState:
    """Store lister state for incremental mode operations"""

    last_listing_date: Optional[datetime] = None
    """Last date when Hackage lister was executed"""


class HackageLister(Lister[HackageListerState, HackageListerPage]):
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
        url: str = BASE_URL,
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
        # Ensure to set this with same value as the http api search endpoint use
        # (50 as of august 2022)
        self.page_size: int = 50
        self.listing_date = datetime.now().astimezone(tz=timezone.utc)

    def state_from_dict(self, d: Dict[str, Any]) -> HackageListerState:
        last_listing_date = d.get("last_listing_date")
        if last_listing_date is not None:
            d["last_listing_date"] = iso8601.parse_date(last_listing_date)
        return HackageListerState(**d)

    def state_to_dict(self, state: HackageListerState) -> Dict[str, Any]:
        d: Dict[str, Optional[str]] = {"last_listing_date": None}
        last_listing_date = state.last_listing_date
        if last_listing_date is not None:
            d["last_listing_date"] = last_listing_date.isoformat()
        return d

    def get_pages(self) -> Iterator[HackageListerPage]:
        """Yield an iterator which returns 'page'

        It uses the http api endpoint `https://hackage.haskell.org/packages/search`
        to get a list of package names from which we build an origin url.

        Results are paginated.
        """
        # Search query
        sq = "(deprecated:any)"

        if self.state.last_listing_date:
            last_str = (
                self.state.last_listing_date.astimezone(tz=timezone.utc)
                .date()
                .isoformat()
            )

            # Incremental mode search query
            sq += "(lastUpload >= %s)" % last_str

        params = {
            "page": 0,
            "sortColumn": "default",
            "sortDirection": "ascending",
            "searchQuery": sq,
        }

        data = self.http_request(
            url=self.PACKAGE_NAMES_URL_PATTERN.format(base_url=self.url),
            method="POST",
            json=params,
        ).json()

        if data.get("pageContents"):
            nb_entries: int = data["numberOfResults"]
            (nb_pages, remainder) = divmod(nb_entries, self.page_size)
            if remainder:
                nb_pages += 1
            # First page
            yield data["pageContents"]
            # Next pages
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

    def finalize(self) -> None:
        self.state.last_listing_date = self.listing_date
        self.updated = True
