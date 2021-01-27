# Copyright (C) 2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from dataclasses import asdict, dataclass
import datetime
import logging
import random
import time
from typing import Any, Dict, Iterator, List, Optional
from urllib.parse import parse_qs, urlparse

import iso8601
import requests

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from .. import USER_AGENT
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

    """  # noqa: E501

    LISTER_NAME = "github"

    API_URL = "https://api.github.com/repositories"
    PAGE_SIZE = 1000

    def __init__(
        self,
        scheduler: SchedulerInterface,
        credentials: CredentialsType = None,
        first_id: Optional[int] = None,
        last_id: Optional[int] = None,
    ):
        super().__init__(
            scheduler=scheduler,
            credentials=credentials,
            url=self.API_URL,
            instance="github",
        )

        self.first_id = first_id
        self.last_id = last_id

        self.relisting = self.first_id is not None or self.last_id is not None

        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/vnd.github.v3+json", "User-Agent": USER_AGENT}
        )

        random.shuffle(self.credentials)

        self.anonymous = not self.credentials

        if self.anonymous:
            logger.warning("No tokens set in configuration, using anonymous mode")

        self.token_index = -1
        self.current_user: Optional[str] = None

        if not self.anonymous:
            # Initialize the first token value in the session headers
            self.set_next_session_token()

    def set_next_session_token(self) -> None:
        """Update the current authentication token with the next one in line."""

        self.token_index = (self.token_index + 1) % len(self.credentials)

        auth = self.credentials[self.token_index]
        if "password" in auth:
            token = auth["password"]
        else:
            token = auth["token"]

        self.current_user = auth["username"]
        logger.debug("Using authentication token for user %s", self.current_user)

        self.session.headers.update({"Authorization": f"token {token}"})

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

            # The following for/else loop handles rate limiting; if successful,
            # it provides the rest of the function with a `response` object.
            #
            # If all tokens are rate-limited, we sleep until the reset time,
            # then `continue` into another iteration of the outer while loop,
            # attempting to get data from the same URL again.

            max_attempts = 1 if self.anonymous else len(self.credentials)
            reset_times: Dict[int, int] = {}  # token index -> time
            for attempt in range(max_attempts):
                response = self.session.get(current_url)
                if not (
                    # GitHub returns inconsistent status codes between unauthenticated
                    # rate limit and authenticated rate limits. Handle both.
                    response.status_code == 429
                    or (self.anonymous and response.status_code == 403)
                ):
                    # Not rate limited, exit this loop.
                    break

                ratelimit_reset = response.headers.get("X-Ratelimit-Reset")
                if ratelimit_reset is None:
                    logger.warning(
                        "Rate-limit reached and X-Ratelimit-Reset value not found. "
                        "Response content: %s",
                        response.content,
                    )
                else:
                    reset_times[self.token_index] = int(ratelimit_reset)

                if not self.anonymous:
                    logger.info(
                        "Rate limit exhausted for current user %s (resetting at %s)",
                        self.current_user,
                        ratelimit_reset,
                    )
                    # Use next token in line
                    self.set_next_session_token()
                    # Wait one second to avoid triggering GitHub's abuse rate limits.
                    time.sleep(1)
            else:
                # All tokens have been rate-limited. What do we do?

                if not reset_times:
                    logger.warning(
                        "No X-Ratelimit-Reset value found in responses for any token; "
                        "Giving up."
                    )
                    break

                sleep_time = max(reset_times.values()) - time.time() + 1
                logger.info(
                    "Rate limits exhausted for all tokens. Sleeping for %f seconds.",
                    sleep_time,
                )
                time.sleep(sleep_time)
                # This goes back to the outer page-by-page loop, doing one more
                # iteration on the same page
                continue

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

        for repo in page:
            pushed_at_str = repo.get("pushed_at")
            pushed_at: Optional[datetime.datetime] = None
            if pushed_at_str:
                pushed_at = iso8601.parse_date(pushed_at_str)

            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                url=repo["html_url"],
                visit_type="git",
                last_update=pushed_at,
            )

    def commit_page(self, page: List[Dict[str, Any]]):
        """Update the currently stored state using the latest listed page"""
        if self.relisting:
            # Don't update internal state when relisting
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
