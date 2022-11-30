# Copyright (C) 2021-2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from dataclasses import asdict, dataclass
import logging
from typing import Any, Dict, Iterator, List
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

    last_page_id: int = 1
    """Id of the last page listed on an incremental pass"""
    last_pkg_name: str = ""
    """Name of the last package inserted at on an incremental pass"""


class HexLister(Lister[HexListerState, HexListerPage]):
    """List origins from the "Hex" forge."""

    LISTER_NAME = "hex"
    VISIT_TYPE = "hex"

    HEX_API_URL = "https://hex.pm/api/"
    PACKAGES_PATH = "packages/"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        instance: str = "hex",
        credentials: CredentialsType = None,
    ):
        super().__init__(
            scheduler=scheduler,
            credentials=credentials,
            url=self.HEX_API_URL,
            instance=instance,
        )
        # TODO: Add authentication support

        self.session.headers.update({"Accept": "application/json"})

    def state_from_dict(self, d: Dict[str, Any]) -> HexListerState:
        return HexListerState(**d)

    def state_to_dict(self, state: HexListerState) -> Dict[str, Any]:
        return asdict(state)

    def get_pages(self) -> Iterator[HexListerPage]:
        page_id = 1
        if self.state.last_page_id is not None:
            page_id = self.state.last_page_id

        url = urljoin(self.url, self.PACKAGES_PATH)

        while page_id is not None:
            body = self.http_request(
                url,
                params={
                    "page": page_id,
                    "sort": "name",
                },  # sort=name is actually the default
            ).json()

            yield body

            page_id += 1  # Consider stopping before yielding?

            if len(body) == 0:
                break  # Consider stopping if number of items < 100?

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
                        release["url"]: {
                            "package": pkg["name"],
                            "version": release["version"],
                            "tar_url": get_tar_url(pkg["name"], release["version"]),
                        }
                        for release in pkg["releases"]
                    }
                },
            )

    def commit_page(self, page: HexListerPage) -> None:
        if len(page) == 0:
            return

        last_pkg_name = page[-1]["name"]

        # incoming page should have alphabetically greater
        # last package name than the one stored in the state
        if last_pkg_name > self.state.last_pkg_name:
            self.state.last_pkg_name = last_pkg_name
            self.state.last_page_id += 1

    def finalize(self) -> None:
        scheduler_state = self.get_state_from_scheduler()

        if self.state.last_page_id > scheduler_state.last_page_id:
            self.updated = True
