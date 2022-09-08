# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from dataclasses import asdict, dataclass
import logging
import random
from typing import Any, Dict, Iterator, List, Optional
from urllib.parse import parse_qs, urljoin, urlparse

import iso8601
import requests
from tenacity.before_sleep import before_sleep_log

from swh.lister.utils import throttling_retry
from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from .. import USER_AGENT
from ..pattern import CredentialsType, Lister

logger = logging.getLogger(__name__)

Repo = Dict[str, Any]


@dataclass
class GogsListerPage:
    repos: Optional[List[Repo]] = None
    next_link: Optional[str] = None


@dataclass
class GogsListerState:
    last_seen_next_link: Optional[str] = None
    """Last link header (could be already visited) during an incremental pass."""
    last_seen_repo_id: Optional[int] = None
    """Last repo id seen during an incremental pass."""


def _parse_page_id(url: Optional[str]) -> int:
    """Parse the page id from a Gogs page url."""
    if url is None:
        return 0

    return int(parse_qs(urlparse(url).query)["page"][0])


class GogsLister(Lister[GogsListerState, GogsListerPage]):

    """List origins from the Gogs

    Gogs API documentation: https://github.com/gogs/docs-api

    The API is protected behind authentication so credentials/API tokens
    are mandatory. It supports pagination and provides next page URL
    through the 'next' value of the 'Link' header. The default value for
    page size ('limit') is 10 but the maximum allowed value is 50.
    """

    LISTER_NAME = "gogs"

    VISIT_TYPE = "git"

    REPO_LIST_PATH = "repos/search"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: str,
        instance: Optional[str] = None,
        api_token: Optional[str] = None,
        page_size: int = 50,
        credentials: CredentialsType = None,
    ):
        super().__init__(
            scheduler=scheduler,
            credentials=credentials,
            url=url,
            instance=instance,
        )

        self.query_params = {
            "limit": page_size,
        }

        self.api_token = api_token
        if self.api_token is None:

            if len(self.credentials) > 0:
                cred = random.choice(self.credentials)
                username = cred.get("username")
                self.api_token = cred["password"]
                logger.info("Using authentication credentials from user %s", username)
            else:
                # Raises an error on Gogs, or a warning on Gitea
                self.on_anonymous_mode()

        self.max_page_limit = 2

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            }
        )

        if self.api_token:
            self.session.headers["Authorization"] = f"token {self.api_token}"

    def on_anonymous_mode(self):
        raise ValueError("No credentials or API token provided")

    def state_from_dict(self, d: Dict[str, Any]) -> GogsListerState:
        return GogsListerState(**d)

    def state_to_dict(self, state: GogsListerState) -> Dict[str, Any]:
        return asdict(state)

    @throttling_retry(before_sleep=before_sleep_log(logger, logging.WARNING))
    def page_request(self, url, params) -> requests.Response:

        logger.debug("Fetching URL %s with params %s", url, params)

        response = self.session.get(url, params=params)

        if response.status_code != 200:
            logger.warning(
                "Unexpected HTTP status code %s on %s: %s",
                response.status_code,
                response.url,
                response.content,
            )
        response.raise_for_status()

        return response

    @classmethod
    def extract_repos(cls, body: Dict[str, Any]) -> List[Repo]:
        fields_filter = ["id", "clone_url", "updated_at"]
        return [{k: r[k] for k in fields_filter} for r in body["data"]]

    def get_pages(self) -> Iterator[GogsListerPage]:
        page_id = 1
        if self.state.last_seen_next_link is not None:
            page_id = _parse_page_id(self.state.last_seen_next_link)

        # base with trailing slash, path without leading slash for urljoin
        next_link: Optional[str] = urljoin(self.url, self.REPO_LIST_PATH)
        response = self.page_request(next_link, {**self.query_params, "page": page_id})

        while next_link is not None:
            repos = self.extract_repos(response.json())

            assert len(response.links) > 0, "API changed: no Link header found"
            if "next" in response.links:
                next_link = response.links["next"]["url"]
            else:
                next_link = None  # Happens for the last page

            yield GogsListerPage(repos=repos, next_link=next_link)

            if next_link is not None:
                response = self.page_request(next_link, {})

    def get_origins_from_page(self, page: GogsListerPage) -> Iterator[ListedOrigin]:
        """Convert a page of Gogs repositories into a list of ListedOrigins"""
        assert self.lister_obj.id is not None
        assert page.repos is not None

        for r in page.repos:
            last_update = iso8601.parse_date(r["updated_at"])

            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                visit_type=self.VISIT_TYPE,
                url=r["clone_url"],
                last_update=last_update,
            )

    def commit_page(self, page: GogsListerPage) -> None:
        last_seen_next_link = page.next_link

        page_id = _parse_page_id(last_seen_next_link)
        state_page_id = _parse_page_id(self.state.last_seen_next_link)

        if page_id > state_page_id:
            self.state.last_seen_next_link = last_seen_next_link

        if (page.repos is not None) and len(page.repos) > 0:
            self.state.last_seen_repo_id = page.repos[-1]["id"]

    def finalize(self) -> None:
        scheduler_state = self.get_state_from_scheduler()

        state_page_id = _parse_page_id(self.state.last_seen_next_link)
        scheduler_page_id = _parse_page_id(scheduler_state.last_seen_next_link)

        state_last_repo_id = self.state.last_seen_repo_id or 0
        scheduler_last_repo_id = scheduler_state.last_seen_repo_id or 0

        if (state_page_id >= scheduler_page_id) and (
            state_last_repo_id > scheduler_last_repo_id
        ):
            self.updated = True  # Marked updated only if it finds new repos
