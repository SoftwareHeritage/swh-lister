# Copyright (C) 2018-2021 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from dataclasses import asdict, dataclass
import logging
import random
from typing import Any, Dict, Iterator, Optional, Tuple
from urllib.parse import parse_qs, urlparse

import requests
from requests.exceptions import HTTPError
from requests.status_codes import codes
from tenacity.before_sleep import before_sleep_log
from urllib3.util import parse_url

from swh.lister import USER_AGENT
from swh.lister.pattern import CredentialsType, Lister
from swh.lister.utils import retry_attempt, throttling_retry
from swh.scheduler.model import ListedOrigin

logger = logging.getLogger(__name__)


@dataclass
class GitLabListerState:
    """State of the GitLabLister"""

    last_seen_next_link: Optional[str] = None
    """Last link header (not visited yet) during an incremental pass

    """


Repository = Dict[str, Any]


@dataclass
class PageResult:
    """Result from a query to a gitlab project api page."""

    repositories: Optional[Tuple[Repository, ...]] = None
    next_page: Optional[str] = None


def _if_rate_limited(retry_state) -> bool:
    """Custom tenacity retry predicate for handling HTTP responses with status code 403
    with specific ratelimit header.

    """
    attempt = retry_attempt(retry_state)
    if attempt.failed:
        exc = attempt.exception()
        return (
            isinstance(exc, HTTPError)
            and exc.response.status_code == codes.forbidden
            and int(exc.response.headers.get("RateLimit-Remaining", "0")) == 0
        )
    return False


def _parse_page_id(url: Optional[str]) -> Optional[int]:
    """Given an url, extract a return the 'page' query parameter associated value or None.

    """
    if not url:
        return None
    # link: https://${project-api}/?...&page=2x...
    query_data = parse_qs(urlparse(url).query)
    page = query_data.get("page")
    if page and len(page) > 0:
        return int(page[0])
    return None


class GitLabLister(Lister[GitLabListerState, PageResult]):
    """List origins for a gitlab instance.

    By default, the lister runs in incremental mode: it lists all repositories,
    starting with the `last_seen_next_link` stored in the scheduler backend.

    Args:
        scheduler: a scheduler instance
        url: the api v4 url of the gitlab instance to visit (e.g.
          https://gitlab.com/api/v4/)
        instance: a specific instance name (e.g. gitlab, tor, git-kernel, ...)
        incremental: defines if incremental listing is activated or not

    """

    LISTER_NAME = "gitlab"

    def __init__(
        self,
        scheduler,
        url: str,
        instance: Optional[str] = None,
        credentials: Optional[CredentialsType] = None,
        incremental: bool = False,
    ):
        if instance is None:
            instance = parse_url(url).host
        super().__init__(
            scheduler=scheduler, url=url, instance=instance, credentials=credentials,
        )
        self.incremental = incremental
        self.last_page: Optional[str] = None

        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/json", "User-Agent": USER_AGENT}
        )

        if len(self.credentials) > 0:
            cred = random.choice(self.credentials)
            logger.info(
                "Using %s credentials from user %s", self.instance, cred["username"]
            )
            api_token = cred["password"]
            if api_token:
                self.session.headers["Authorization"] = f"Bearer {api_token}"

    def state_from_dict(self, d: Dict[str, Any]) -> GitLabListerState:
        return GitLabListerState(**d)

    def state_to_dict(self, state: GitLabListerState) -> Dict[str, Any]:
        return asdict(state)

    @throttling_retry(
        retry=_if_rate_limited, before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def get_page_result(self, url: str) -> PageResult:
        logger.debug("Fetching URL %s", url)
        response = self.session.get(url)
        if response.status_code != 200:
            logger.warning(
                "Unexpected HTTP status code %s on %s: %s",
                response.status_code,
                response.url,
                response.content,
            )
        response.raise_for_status()
        repositories: Tuple[Repository, ...] = tuple(response.json())
        if hasattr(response, "links") and response.links.get("next"):
            next_page = response.links["next"]["url"]
        else:
            next_page = None

        return PageResult(repositories, next_page)

    def page_url(self, page_id: int) -> str:
        return f"{self.url}projects?page={page_id}&order_by=id&sort=asc&per_page=20"

    def get_pages(self) -> Iterator[PageResult]:
        next_page: Optional[str]
        if self.incremental and self.state and self.state.last_seen_next_link:
            next_page = self.state.last_seen_next_link
        else:
            next_page = self.page_url(1)

        while next_page:
            self.last_page = next_page
            page_result = self.get_page_result(next_page)
            yield page_result
            next_page = page_result.next_page

    def get_origins_from_page(self, page_result: PageResult) -> Iterator[ListedOrigin]:
        assert self.lister_obj.id is not None

        repositories = page_result.repositories if page_result.repositories else []
        for repo in repositories:
            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                url=repo["http_url_to_repo"],
                visit_type="git",
                # TODO: Support "last_activity_at" as update information
                # last_update=repo["last_activity_at"],
            )

    def commit_page(self, page_result: PageResult) -> None:
        """Update currently stored state using the latest listed "next" page if relevant.

        Relevancy is determined by the next_page link whose 'page' id must be strictly
        superior to the currently stored one.

        Note: this is a noop for full listing mode

        """
        if self.incremental:
            # link: https://${project-api}/?...&page=2x...
            next_page = page_result.next_page
            if not next_page and self.last_page:
                next_page = self.last_page

            if next_page:
                page_id = _parse_page_id(next_page)
                previous_next_page = self.state.last_seen_next_link
                previous_page_id = _parse_page_id(previous_next_page)

                if previous_next_page is None or (
                    previous_page_id and page_id and previous_page_id < page_id
                ):
                    self.state.last_seen_next_link = next_page

    def finalize(self) -> None:
        """finalize the lister state when relevant (see `fn:commit_page` for details)

        Note: this is a noop for full listing mode

        """
        next_page = self.state.last_seen_next_link
        if self.incremental and next_page:
            # link: https://${project-api}/?...&page=2x...
            next_page_id = _parse_page_id(next_page)
            scheduler_state = self.get_state_from_scheduler()
            previous_next_page_id = _parse_page_id(scheduler_state.last_seen_next_link)

            if (not previous_next_page_id and next_page_id) or (
                previous_next_page_id
                and next_page_id
                and previous_next_page_id < next_page_id
            ):
                self.updated = True
