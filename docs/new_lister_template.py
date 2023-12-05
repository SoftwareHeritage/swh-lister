# Copyright (C) 2021-2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from dataclasses import asdict, dataclass
import logging
from typing import Any, Dict, Iterator, List
from urllib.parse import urljoin

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, Lister

logger = logging.getLogger(__name__)

# Aliasing the page results returned by `get_pages` method from the lister.
NewForgeListerPage = List[Dict[str, Any]]


@dataclass
class NewForgeListerState:
    """The NewForgeLister instance state. This is used for incremental listing."""

    current: str = ""
    """Id of the last origin listed on an incremental pass"""


# If there is no need to keep state, subclass StatelessLister[NewForgeListerPage]
class NewForgeLister(Lister[NewForgeListerState, NewForgeListerPage]):
    """List origins from the "NewForge" forge."""

    # Part of the lister API, that identifies this lister
    LISTER_NAME = ""
    # (Optional) CVS type of the origins listed by this lister, if constant
    VISIT_TYPE = ""

    # Instance URLs include the hostname and the common path prefix of processed URLs
    EXAMPLE_BASE_URL = "https://netloc/api/v1/"
    # Path of a specific resource to process, to join the base URL with
    EXAMPLE_PATH = "origins/list"

    def __init__(
        self,
        # Required
        scheduler: SchedulerInterface,
        # Instance URL, required for multi-instances listers (e.g gitlab, ...)
        url: str,
        # Instance name (free form) required for multi-instance listers,
        # or computed from `url`
        instance: str,
        # Required whether lister supports authentication or not
        credentials: CredentialsType = None,
    ):
        super().__init__(
            scheduler=scheduler,
            credentials=credentials,
            url=url,
            instance=instance,
        )

        self.session.headers.update({"Accept": "application/json"})

    def state_from_dict(self, d: Dict[str, Any]) -> NewForgeListerState:
        return NewForgeListerState(**d)

    def state_to_dict(self, state: NewForgeListerState) -> Dict[str, Any]:
        return asdict(state)

    def get_pages(self) -> Iterator[NewForgeListerPage]:
        # The algorithm depends on the service, but should request data reliably,
        # following pagination if relevant and yielding pages in a streaming fashion.
        # If incremental listing is supported, initialize from saved lister state.
        # Make use of any next page URL provided.
        # Simplify the results early to ease testing and debugging.

        # Initialize from the lister saved state
        current = ""
        if self.state.current is not None:
            current = self.state.current

        # Construct the URL of a service endpoint, the lister can have others to fetch
        url = urljoin(self.url, self.EXAMPLE_PATH)

        while current is not None:
            # Parametrize the request for incremental listing
            body = self.http_request(url, params={"current": current}).json()

            # Simplify the page if possible to only the necessary elements
            # and yield it
            yield body

            # Get the next page parameter or end the loop when there is none
            current = body.get("next")

    def get_origins_from_page(self, page: NewForgeListerPage) -> Iterator[ListedOrigin]:
        """Convert a page of NewForgeLister repositories into a list of ListedOrigins"""
        assert self.lister_obj.id is not None

        for element in page:
            yield ListedOrigin(
                # Required. Should use this value.
                lister_id=self.lister_obj.id,
                # Required. Visit type of the currently processed origin
                visit_type=self.VISIT_TYPE,
                # Required. URL corresponding to the origin for loaders to ingest
                url=...,
                # Should get it if the service provides it and if it induces no
                # substantial additional processing cost
                last_update=...,
            )

    def commit_page(self, page: NewForgeListerPage) -> None:
        # Update the lister state to the latest `current`
        current = page[-1]["current"]

        if current > self.state.current:
            self.state.current = current

    def finalize(self) -> None:
        # Pull fresh lister state from the scheduler backend, in case multiple
        # listers run concurrently
        scheduler_state = self.get_state_from_scheduler()

        # Update the lister state in the backend only if `current` is fresher than
        # the one stored in the database.
        if self.state.current > scheduler_state.current:
            self.updated = True
