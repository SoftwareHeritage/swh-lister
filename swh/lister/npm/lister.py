# Copyright (C) 2018-2025 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from dataclasses import asdict, dataclass
import logging
from typing import Any, Dict, Iterator, List, Optional

from swh.lister.pattern import CredentialsType, Lister
from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin
from swh.scheduler.utils import utcnow

logger = logging.getLogger(__name__)


@dataclass
class NpmListerState:
    """State of npm lister"""

    last_seq: Optional[int] = None


class NpmLister(Lister[NpmListerState, List[Dict[str, Any]]]):
    """
    List packages referenced by the changes API of the npm registry
    by last modification order.

    The lister is based on the npm replication API powered by a
    CouchDB database (https://docs.couchdb.org/en/stable/api/database/).

    Args:
        scheduler: a scheduler instance
        page_size: number of packages info to return per page when querying npm API
        incremental: defines if incremental listing should be used, in that case
            only modified or new packages since last incremental listing operation
            will be returned, otherwise all packages referenced by the NPM changes
            API will be listed in last modification order
    """

    LISTER_NAME = "npm"
    INSTANCE = "npm"

    NPM_API_BASE_URL = "https://replicate.npmjs.com"
    NPM_API_CHANGES_URL = f"{NPM_API_BASE_URL}/_changes"
    PACKAGE_URL_TEMPLATE = "https://www.npmjs.com/package/{package_name}"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: str = NPM_API_CHANGES_URL,
        instance: str = INSTANCE,
        page_size: int = 10000,
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
        self.incremental = incremental
        self.listing_date = utcnow()

    def state_from_dict(self, d: Dict[str, Any]) -> NpmListerState:
        return NpmListerState(**d)

    def state_to_dict(self, state: NpmListerState) -> Dict[str, Any]:
        return asdict(state)

    def request_params(self, last_seq: str) -> Dict[str, Any]:
        # include package JSON document to get its last update date
        params: Dict[str, Any] = {"limit": self.page_size}
        params["since"] = last_seq
        return params

    def get_pages(self) -> Iterator[List[Dict[str, Any]]]:
        last_seq: str = "0"
        if (
            self.incremental
            and self.state is not None
            and self.state.last_seq is not None
        ):
            last_seq = str(self.state.last_seq)

        while True:
            response = self.http_request(self.url, params=self.request_params(last_seq))

            data = response.json()
            page = data["results"]

            if not page:
                break

            yield page

            if len(page) < self.page_size:
                break

            last_seq = str(page[-1]["seq"])

    def get_origins_from_page(
        self, page: List[Dict[str, Any]]
    ) -> Iterator[ListedOrigin]:
        """Convert a page of Npm repositories into a list of ListedOrigin."""
        assert self.lister_obj.id is not None

        for package in page:
            if package.get("deleted"):
                continue
            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                url=self.PACKAGE_URL_TEMPLATE.format(package_name=package["id"]),
                visit_type="npm",
                last_update=self.listing_date,
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
