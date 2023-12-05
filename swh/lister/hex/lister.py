# Copyright (C) 2021-2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from dataclasses import asdict, dataclass
import logging
from typing import Any, Dict, Iterator, List, Optional
from urllib.parse import urljoin

import iso8601

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, Lister

logger = logging.getLogger(__name__)

HexListerPage = List[Dict[str, Any]]


def get_tar_url(pkg_name: str, release_version: str):
    return f"https://repo.hex.pm/tarballs/{pkg_name}-{release_version}.tar"


@dataclass
class HexListerState:
    """The HexLister instance state. This is used for incremental listing."""

    # Note: Default values are used only when the lister is run for the first time.

    page_updated_at: str = "0001-01-01T00:00:00.000000Z"  # Min datetime
    """`updated_at` value of the last seen package in the page."""


class HexLister(Lister[HexListerState, HexListerPage]):
    """List origins from the Hex.pm"""

    LISTER_NAME = "hex"
    VISIT_TYPE = "hex"

    HEX_API_URL = "https://hex.pm/api/"
    PACKAGES_PATH = "packages/"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: str = HEX_API_URL,
        instance: str = LISTER_NAME,
        page_size: int = 100,
        credentials: CredentialsType = None,
        max_origins_per_page: Optional[int] = None,
        max_pages: Optional[int] = None,
        enable_origins: bool = True,
    ):
        super().__init__(
            scheduler=scheduler,
            credentials=credentials,
            url=url,
            instance=instance,
            max_origins_per_page=max_origins_per_page,
            max_pages=max_pages,
            enable_origins=enable_origins,
        )
        # TODO: Add authentication support
        self.page_size = page_size

        self.session.headers.update({"Accept": "application/json"})

    def state_from_dict(self, d: Dict[str, Any]) -> HexListerState:
        return HexListerState(**d)

    def state_to_dict(self, state: HexListerState) -> Dict[str, Any]:
        return asdict(state)

    def get_pages(self) -> Iterator[HexListerPage]:
        url = urljoin(self.url, self.PACKAGES_PATH)

        while True:
            body = self.http_request(  # This also logs the request
                url,
                params={
                    "search": f"updated_after:{self.state.page_updated_at}",
                    # We expect 100 packages per page. The API doesn't allow us to change that.
                },
            ).json()

            yield body

            if len(body) < self.page_size:  # Always 100 in when running on the real API
                break

    def get_origins_from_page(self, page: HexListerPage) -> Iterator[ListedOrigin]:
        """Convert a page of HexLister repositories into a list of ListedOrigins"""
        assert self.lister_obj.id is not None

        for pkg in page:
            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                visit_type=self.VISIT_TYPE,
                url=pkg["html_url"],
                last_update=iso8601.parse_date(pkg["updated_at"]),
                extra_loader_arguments={
                    "releases": {
                        release["version"]: {
                            "name": pkg["name"],
                            "release_url": release["url"],
                            "tarball_url": get_tar_url(pkg["name"], release["version"]),
                            "inserted_at": release["inserted_at"],
                        }
                        for release in pkg["releases"]
                    }
                },
            )

    def commit_page(self, page: HexListerPage) -> None:
        if len(page) == 0:
            return

        page_updated_at = page[-1]["updated_at"]
        """`page_updated_at` is same as `updated_at` of the last package in the page."""

        if (
            iso8601.parse_date(page_updated_at)
            > iso8601.parse_date(self.state.page_updated_at)
            and len(page) > 0
        ):
            # There's one edge case where `updated_at` don't change between two pages.
            # But that seems practically impossible because we have 100 packages
            # per page and the `updated_at` keeps on increasing with time.
            self.state.page_updated_at = page_updated_at

    def finalize(self) -> None:
        scheduler_state = self.get_state_from_scheduler()

        # Mark the lister as updated only if it finds any updated repos
        if iso8601.parse_date(self.state.page_updated_at) > iso8601.parse_date(
            scheduler_state.page_updated_at
        ):
            self.updated = True  # This will update the lister state in the scheduler
