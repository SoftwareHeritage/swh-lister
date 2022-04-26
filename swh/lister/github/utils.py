# Copyright (C) 2020-2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging
import random
import time
from typing import Dict, List, Optional

import requests
from tenacity import (
    retry,
    retry_any,
    retry_if_exception_type,
    retry_if_result,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class RateLimited(Exception):
    def __init__(self, response):
        self.reset_time: Optional[int]

        # Figure out how long we need to sleep because of that rate limit
        ratelimit_reset = response.headers.get("X-Ratelimit-Reset")
        retry_after = response.headers.get("Retry-After")
        if ratelimit_reset is not None:
            self.reset_time = int(ratelimit_reset)
        elif retry_after is not None:
            self.reset_time = int(time.time()) + int(retry_after) + 1
        else:
            logger.warning(
                "Received a rate-limit-like status code %s, but no rate-limit "
                "headers set. Response content: %s",
                response.status_code,
                response.content,
            )
            self.reset_time = None
        self.response = response


class MissingRateLimitReset(Exception):
    pass


class GitHubSession:
    """Manages a :class:`requests.Session` with (optionally) multiple credentials,
    and cycles through them when reaching rate-limits."""

    def __init__(
        self, user_agent: str, credentials: Optional[List[Dict[str, str]]] = None
    ) -> None:
        """Initialize a requests session with the proper headers for requests to
        GitHub."""
        self.credentials = credentials
        if self.credentials:
            random.shuffle(self.credentials)

        self.session = requests.Session()

        self.session.headers.update(
            {"Accept": "application/vnd.github.v3+json", "User-Agent": user_agent}
        )

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

        assert self.credentials

        self.token_index = (self.token_index + 1) % len(self.credentials)

        auth = self.credentials[self.token_index]

        self.current_user = auth["username"]
        logger.debug("Using authentication token for user %s", self.current_user)

        if "password" in auth:
            token = auth["password"]
        else:
            token = auth["token"]

        self.session.headers.update({"Authorization": f"token {token}"})

    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_any(
            # ChunkedEncodingErrors happen when the TLS connection gets reset, e.g.
            # when running the lister on a connection with high latency
            retry_if_exception_type(requests.exceptions.ChunkedEncodingError),
            # 502 status codes happen for a Server Error, sometimes
            retry_if_result(lambda r: r.status_code == 502),
        ),
    )
    def _request(self, url: str) -> requests.Response:
        response = self.session.get(url)

        if (
            # GitHub returns inconsistent status codes between unauthenticated
            # rate limit and authenticated rate limits. Handle both.
            response.status_code == 429
            or (self.anonymous and response.status_code == 403)
        ):
            raise RateLimited(response)

        return response

    def request(self, url) -> requests.Response:
        """Repeatedly requests the given URL, cycling through credentials and sleeping
        if necessary; until either a successful response or :exc:`MissingRateLimitReset`
        """
        # The following for/else loop handles rate limiting; if successful,
        # it provides the rest of the function with a `response` object.
        #
        # If all tokens are rate-limited, we sleep until the reset time,
        # then `continue` into another iteration of the outer while loop,
        # attempting to get data from the same URL again.

        while True:
            max_attempts = len(self.credentials) if self.credentials else 1
            reset_times: Dict[int, int] = {}  # token index -> time
            for attempt in range(max_attempts):
                try:
                    return self._request(url)
                except RateLimited as e:
                    reset_info = "(unknown reset)"
                    if e.reset_time is not None:
                        reset_times[self.token_index] = e.reset_time
                        reset_info = "(resetting in %ss)" % (e.reset_time - time.time())

                    if not self.anonymous:
                        logger.info(
                            "Rate limit exhausted for current user %s %s",
                            self.current_user,
                            reset_info,
                        )
                        # Use next token in line
                        self.set_next_session_token()
                        # Wait one second to avoid triggering GitHub's abuse rate limits
                        time.sleep(1)

            # All tokens have been rate-limited. What do we do?

            if not reset_times:
                logger.warning(
                    "No X-Ratelimit-Reset value found in responses for any token; "
                    "Giving up."
                )
                raise MissingRateLimitReset()

            sleep_time = max(reset_times.values()) - time.time() + 1
            logger.info(
                "Rate limits exhausted for all tokens. Sleeping for %f seconds.",
                sleep_time,
            )
            time.sleep(sleep_time)
