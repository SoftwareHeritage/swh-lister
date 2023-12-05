# Copyright (C) 2018-2023 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from dataclasses import asdict, dataclass
import logging
from typing import Any, Dict, Iterator, List, Optional

import iso8601

from swh.lister.pattern import CredentialsType, Lister
from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

logger = logging.getLogger(__name__)


@dataclass
class NpmListerState:
    """State of npm lister"""

    last_seq: Optional[int] = None


class NpmLister(Lister[NpmListerState, List[Dict[str, Any]]]):
    """
    List all packages hosted on the npm registry.

    The lister is based on the npm replication API powered by a
    CouchDB database (https://docs.couchdb.org/en/stable/api/database/).

    Args:
        scheduler: a scheduler instance
        page_size: number of packages info to return per page when querying npm API
        incremental: defines if incremental listing should be used, in that case
            only modified or new packages since last incremental listing operation
            will be returned, otherwise all packages will be listed in lexicographical
            order

    """

    LISTER_NAME = "npm"
    INSTANCE = "npm"

    API_BASE_URL = "https://replicate.npmjs.com"
    API_INCREMENTAL_LISTING_URL = f"{API_BASE_URL}/_changes"
    API_FULL_LISTING_URL = f"{API_BASE_URL}/_all_docs"
    PACKAGE_URL_TEMPLATE = "https://www.npmjs.com/package/{package_name}"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: str = API_FULL_LISTING_URL,
        instance: str = INSTANCE,
        page_size: int = 1000,
        incremental: bool = False,
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

        self.page_size = page_size
        if not incremental:
            # in full listing mode, first package in each page corresponds to the one
            # provided as the startkey query parameter value, so we increment the page
            # size by one to avoid double package processing
            self.page_size += 1
        else:
            self.url = self.API_INCREMENTAL_LISTING_URL
        self.incremental = incremental

        self.session.headers.update({"Accept": "application/json"})

    def state_from_dict(self, d: Dict[str, Any]) -> NpmListerState:
        return NpmListerState(**d)

    def state_to_dict(self, state: NpmListerState) -> Dict[str, Any]:
        return asdict(state)

    def request_params(self, last_package_id: str) -> Dict[str, Any]:
        # include package JSON document to get its last update date
        params = {"limit": self.page_size, "include_docs": "true"}
        if self.incremental:
            params["since"] = last_package_id
        else:
            params["startkey"] = last_package_id
        return params

    def get_pages(self) -> Iterator[List[Dict[str, Any]]]:
        last_package_id: str = "0" if self.incremental else '""'
        if (
            self.incremental
            and self.state is not None
            and self.state.last_seq is not None
        ):
            last_package_id = str(self.state.last_seq)

        while True:
            response = self.http_request(
                self.url, params=self.request_params(last_package_id)
            )

            data = response.json()
            page = data["results"] if self.incremental else data["rows"]

            if not page:
                break

            if self.incremental or len(page) < self.page_size:
                yield page
            else:
                yield page[:-1]

            if len(page) < self.page_size:
                break

            last_package_id = (
                str(page[-1]["seq"]) if self.incremental else f'"{page[-1]["id"]}"'
            )

    def get_origins_from_page(
        self, page: List[Dict[str, Any]]
    ) -> Iterator[ListedOrigin]:
        """Convert a page of Npm repositories into a list of ListedOrigin."""
        assert self.lister_obj.id is not None

        for package in page:
            # no source code to archive here
            if not package["doc"].get("versions", {}):
                continue

            package_name = package["doc"]["name"]
            package_latest_version = (
                package["doc"].get("dist-tags", {}).get("latest", "")
            )

            last_update = None
            if package_latest_version in package["doc"].get("time", {}):
                last_update = iso8601.parse_date(
                    package["doc"]["time"][package_latest_version]
                )

            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                url=self.PACKAGE_URL_TEMPLATE.format(package_name=package_name),
                visit_type="npm",
                last_update=last_update,
            )

    def commit_page(self, page: List[Dict[str, Any]]):
        """Update the currently stored state using the latest listed page."""
        if self.incremental:
            last_package = page[-1]
            last_seq = last_package["seq"]

            if self.state.last_seq is None or last_seq > self.state.last_seq:
                self.state.last_seq = last_seq

    def finalize(self):
        if self.incremental and self.state.last_seq is not None:
            scheduler_state = self.get_state_from_scheduler()

            if (
                scheduler_state.last_seq is None
                or self.state.last_seq > scheduler_state.last_seq
            ):
                self.updated = True
