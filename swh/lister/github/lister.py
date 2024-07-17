# Copyright (C) 2020-2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from dataclasses import asdict, dataclass
import datetime
import logging
from typing import Any, Dict, Iterator, List, Optional, Set
from urllib.parse import parse_qs, urlparse

import iso8601

from swh.core.github.utils import MissingRateLimitReset
from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, Lister

logger = logging.getLogger(__name__)


@dataclass
class GitHubListerState:
    """State of the GitHub lister"""

    last_seen_id: int = 0
    """Numeric id of the last repository listed on an incremental pass"""


class GitHubLister(Lister[GitHubListerState, List[Dict[str, Any]]]):
    """List origins from GitHub.

    By default, the lister runs in incremental mode: it lists all repositories,
    starting with the `last_seen_id` stored in the scheduler backend.

    Providing the `first_id` and `last_id` arguments enables the "relisting" mode: in
    that mode, the lister finds the origins present in the range **excluding**
    `first_id` and **including** `last_id`. In this mode, the lister can overrun the
    `last_id`: it will always record all the origins seen in a given page. As the lister
    is fully idempotent, this is not a practical problem. Once relisting completes, the
    lister state in the scheduler backend is not updated.

    When the config contains a set of credentials, we shuffle this list at the beginning
    of the listing. To follow GitHub's `abuse rate limit policy`_, we keep using the
    same token over and over again, until its rate limit runs out. Once that happens, we
    switch to the next token over in our shuffled list.

    When a request fails with a rate limit exception for all tokens, we pause the
    listing until the largest value for X-Ratelimit-Reset over all tokens.

    When the credentials aren't set in the lister config, the lister can run in
    anonymous mode too (e.g. for testing purposes).

    .. _abuse rate limit policy: https://developer.github.com/v3/guides/best-practices-for-integrators/#dealing-with-abuse-rate-limits


    Args:
      first_id: the id of the first repo to list
      last_id: stop listing after seeing a repo with an id higher than this value.

    """  # noqa: B950

    LISTER_NAME = "github"
    INSTANCE = "github"

    API_URL = "https://api.github.com/repositories"
    PAGE_SIZE = 1000

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: str = API_URL,
        instance: str = INSTANCE,
        credentials: CredentialsType = None,
        max_origins_per_page: Optional[int] = None,
        max_pages: Optional[int] = None,
        enable_origins: bool = True,
        first_id: Optional[int] = None,
        last_id: Optional[int] = None,
    ):
        super().__init__(
            scheduler=scheduler,
            credentials=credentials,
            url=url,
            instance=instance,
            with_github_session=True,
            max_origins_per_page=max_origins_per_page,
            max_pages=max_pages,
            enable_origins=enable_origins,
        )

        self.first_id = first_id
        self.last_id = last_id

        self.relisting = self.first_id is not None or self.last_id is not None

    def state_from_dict(self, d: Dict[str, Any]) -> GitHubListerState:
        return GitHubListerState(**d)

    def state_to_dict(self, state: GitHubListerState) -> Dict[str, Any]:
        return asdict(state)

    def get_pages(self) -> Iterator[List[Dict[str, Any]]]:
        current_id = 0
        if self.first_id is not None:
            current_id = self.first_id
        elif self.state is not None:
            current_id = self.state.last_seen_id

        current_url = f"{self.API_URL}?since={current_id}&per_page={self.PAGE_SIZE}"

        while self.last_id is None or current_id < self.last_id:
            logger.debug("Getting page %s", current_url)

            try:
                assert self.github_session is not None
                response = self.github_session.request(current_url)
            except MissingRateLimitReset:
                # Give up
                break

            # We've successfully retrieved a (non-ratelimited) `response`. We
            # still need to check it for validity.

            if response.status_code != 200:
                logger.warning(
                    "Got unexpected status_code %s: %s",
                    response.status_code,
                    response.content,
                )
                break

            yield response.json()

            if "next" not in response.links:
                # No `next` link, we've reached the end of the world
                logger.debug(
                    "No next link found in the response headers, all caught up"
                )
                break

            # GitHub strongly advises to use the next link directly. We still
            # parse it to get the id of the last repository we've reached so
            # far.
            next_url = response.links["next"]["url"]
            parsed_url = urlparse(next_url)
            if not parsed_url.query:
                logger.warning("Failed to parse url %s", next_url)
                break

            parsed_query = parse_qs(parsed_url.query)
            current_id = int(parsed_query["since"][0])
            current_url = next_url

    def get_origins_from_page(
        self, page: List[Dict[str, Any]]
    ) -> Iterator[ListedOrigin]:
        """Convert a page of GitHub repositories into a list of ListedOrigins.

        This records the html_url, as well as the pushed_at value if it exists.
        """
        assert self.lister_obj.id is not None

        seen_in_page: Set[str] = set()

        for repo in page:
            if not repo:
                # null repositories in listings happen sometimes...
                continue

            if repo["html_url"] in seen_in_page:
                continue
            seen_in_page.add(repo["html_url"])

            pushed_at_str = repo.get("pushed_at")
            pushed_at: Optional[datetime.datetime] = None
            if pushed_at_str:
                pushed_at = iso8601.parse_date(pushed_at_str)

            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                url=repo["html_url"],
                visit_type="git",
                last_update=pushed_at,
                is_fork=repo.get("fork"),
            )

    def commit_page(self, page: List[Dict[str, Any]]):
        """Update the currently stored state using the latest listed page"""
        if self.relisting:
            # Don't update internal state when relisting
            return

        if not page:
            # Sometimes, when you reach the end of the world, GitHub returns an empty
            # page of repositories
            return

        last_id = page[-1]["id"]

        if last_id > self.state.last_seen_id:
            self.state.last_seen_id = last_id

    def finalize(self):
        if self.relisting:
            return

        # Pull fresh lister state from the scheduler backend
        scheduler_state = self.get_state_from_scheduler()

        # Update the lister state in the backend only if the last seen id of
        # the current run is higher than that stored in the database.
        if self.state.last_seen_id > scheduler_state.last_seen_id:
            self.updated = True
