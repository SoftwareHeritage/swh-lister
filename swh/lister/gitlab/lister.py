# Copyright (C) 2018-2023 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from dataclasses import asdict, dataclass
import logging
import random
from typing import Any, Dict, Iterator, List, Optional, Tuple
from urllib.parse import parse_qs, urlencode, urlparse

import iso8601
from requests.exceptions import HTTPError
from requests.status_codes import codes
from tenacity.before_sleep import before_sleep_log

from swh.core.retry import http_retry, is_retryable_exception
from swh.lister.pattern import CredentialsType, Lister
from swh.scheduler.model import ListedOrigin

logger = logging.getLogger(__name__)


# Some instance provides hg_git type which can be ingested as hg origins
VCS_MAPPING = {"hg_git": "hg"}


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
    attempt = retry_state.outcome
    if attempt.failed:
        exc = attempt.exception()
        return (
            isinstance(exc, HTTPError)
            and exc.response is not None
            and exc.response.status_code == codes.forbidden
            and int(exc.response.headers.get("RateLimit-Remaining", "0")) == 0
        ) or is_retryable_exception(exc)
    return False


def _parse_id_after(url: Optional[str]) -> Optional[int]:
    """Given an url, extract a return the 'id_after' query parameter associated value
    or None.

    This is the the repository id used for pagination purposes.

    """
    if not url:
        return None
    # link: https://${project-api}/?...&id_after=2x...
    query_data = parse_qs(urlparse(url).query)
    page = query_data.get("id_after")
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
        instance: a specific instance name (e.g. gitlab, tor, git-kernel, ...),
            url network location will be used if not provided
        incremental: defines if incremental listing is activated or not
        ignored_project_prefixes: List of prefixes of project paths to ignore

    """

    def __init__(
        self,
        scheduler,
        url: Optional[str] = None,
        name: Optional[str] = "gitlab",
        instance: Optional[str] = None,
        credentials: Optional[CredentialsType] = None,
        max_origins_per_page: Optional[int] = None,
        max_pages: Optional[int] = None,
        enable_origins: bool = True,
        incremental: bool = False,
        ignored_project_prefixes: Optional[List[str]] = None,
    ):
        if name is not None:
            self.LISTER_NAME = name
        super().__init__(
            scheduler=scheduler,
            # if url is not provided, url will be built in the `build_url` method
            url=url.rstrip("/") if url else None,
            instance=instance,
            credentials=credentials,
            max_origins_per_page=max_origins_per_page,
            max_pages=max_pages,
            enable_origins=enable_origins,
        )
        self.incremental = incremental
        self.last_page: Optional[str] = None
        self.per_page = 100
        self.ignored_project_prefixes: Optional[Tuple[str, ...]] = None
        if ignored_project_prefixes:
            self.ignored_project_prefixes = tuple(ignored_project_prefixes)

        self.session.headers.update({"Accept": "application/json"})

        if len(self.credentials) > 0:
            cred = random.choice(self.credentials)
            logger.info(
                "Using %s credentials from user %s", self.instance, cred["username"]
            )
            api_token = cred["password"]
            if api_token:
                self.session.headers["Authorization"] = f"Bearer {api_token}"

    def build_url(self, instance: str) -> str:
        """Build gitlab api url."""
        prefix_url = super().build_url(instance)
        return f"{prefix_url}/api/v4"

    def state_from_dict(self, d: Dict[str, Any]) -> GitLabListerState:
        return GitLabListerState(**d)

    def state_to_dict(self, state: GitLabListerState) -> Dict[str, Any]:
        return asdict(state)

    @http_retry(
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

        # GitLab API can return errors 500 when listing projects.
        # https://gitlab.com/gitlab-org/gitlab/-/issues/262629
        # To avoid ending the listing prematurely, skip buggy URLs and move
        # to next pages.
        if response.status_code == 500:
            id_after = _parse_id_after(url)
            assert id_after is not None
            while True:
                next_id_after = id_after + self.per_page
                url = url.replace(f"id_after={id_after}", f"id_after={next_id_after}")
                response = self.session.get(url)
                if response.status_code == 200:
                    break
                else:
                    id_after = next_id_after
        else:
            response.raise_for_status()

        repositories: Tuple[Repository, ...] = tuple(response.json())
        if hasattr(response, "links") and response.links.get("next"):
            next_page = response.links["next"]["url"]
        else:
            next_page = None

        return PageResult(repositories, next_page)

    def page_url(self, id_after: Optional[int] = None) -> str:
        parameters = {
            "pagination": "keyset",
            "order_by": "id",
            "sort": "asc",
            "simple": "true",
            "per_page": f"{self.per_page}",
        }
        if id_after is not None:
            parameters["id_after"] = str(id_after)
        return f"{self.url}/projects?{urlencode(parameters)}"

    def get_pages(self) -> Iterator[PageResult]:
        next_page: Optional[str]
        if self.incremental and self.state and self.state.last_seen_next_link:
            next_page = self.state.last_seen_next_link
        else:
            next_page = self.page_url()

        while next_page:
            self.last_page = next_page
            page_result = self.get_page_result(next_page)
            yield page_result
            next_page = page_result.next_page

    def get_origins_from_page(self, page_result: PageResult) -> Iterator[ListedOrigin]:
        assert self.lister_obj.id is not None

        repositories = page_result.repositories if page_result.repositories else []
        for repo in repositories:
            if self.ignored_project_prefixes and repo["path_with_namespace"].startswith(
                self.ignored_project_prefixes
            ):
                continue
            visit_type = repo.get("vcs_type", "git")
            visit_type = VCS_MAPPING.get(visit_type, visit_type)
            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                url=repo["http_url_to_repo"],
                visit_type=visit_type,
                last_update=iso8601.parse_date(repo["last_activity_at"]),
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
                id_after = _parse_id_after(next_page)
                previous_next_page = self.state.last_seen_next_link
                previous_id_after = _parse_id_after(previous_next_page)

                if previous_next_page is None or (
                    previous_id_after and id_after and previous_id_after < id_after
                ):
                    self.state.last_seen_next_link = next_page

    def finalize(self) -> None:
        """finalize the lister state when relevant (see `fn:commit_page` for details)

        Note: this is a noop for full listing mode

        """
        next_page = self.state.last_seen_next_link
        if self.incremental and next_page:
            # link: https://${project-api}/?...&page=2x...
            next_id_after = _parse_id_after(next_page)
            scheduler_state = self.get_state_from_scheduler()
            previous_next_id_after = _parse_id_after(
                scheduler_state.last_seen_next_link
            )

            if (not previous_next_id_after and next_id_after) or (
                previous_next_id_after
                and next_id_after
                and previous_next_id_after < next_id_after
            ):
                self.updated = True
