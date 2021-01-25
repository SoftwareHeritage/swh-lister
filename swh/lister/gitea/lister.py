# Copyright (C) 2018-2021 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging
import random
from typing import Any, Dict, Iterator, List, Optional
from urllib.parse import urljoin

import iso8601
import requests
from tenacity.before_sleep import before_sleep_log
from urllib3.util import parse_url

from swh.lister.utils import throttling_retry
from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from .. import USER_AGENT
from ..pattern import CredentialsType, StatelessLister

logger = logging.getLogger(__name__)

RepoListPage = List[Dict[str, Any]]


class GiteaLister(StatelessLister[RepoListPage]):
    """List origins from Gitea.

    Gitea API documentation: https://try.gitea.io/api/swagger

    The API does pagination and provides navigation URLs through the 'Link' header.
    The default value for page size is the maximum value observed on the instances
    accessible at https://try.gitea.io/api/v1/ and https://codeberg.org/api/v1/."""

    LISTER_NAME = "gitea"

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
        if instance is None:
            instance = parse_url(url).host

        super().__init__(
            scheduler=scheduler, credentials=credentials, url=url, instance=instance,
        )

        self.query_params = {
            "sort": "id",
            "order": "asc",
            "limit": page_size,
            "page": 1,
        }

        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/json", "User-Agent": USER_AGENT,}
        )

        if api_token is None:
            if len(self.credentials) > 0:
                cred = random.choice(self.credentials)
                username = cred.get("username")
                api_token = cred["password"]
                logger.warning(
                    "Using authentication token from user %s", username or "???"
                )
            else:
                logger.warning(
                    "No authentication token set in configuration, using anonymous mode"
                )

        if api_token:
            self.session.headers["Authorization"] = "Token %s" % api_token

    @throttling_retry(before_sleep=before_sleep_log(logger, logging.WARNING))
    def page_request(self, url: str, params: Dict[str, Any]) -> requests.Response:

        logger.info("Fetching URL %s with params %s", url, params)

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
    def results_simplified(cls, body: Dict[str, RepoListPage]) -> RepoListPage:
        fields_filter = ["id", "clone_url", "updated_at"]
        return [{k: r[k] for k in fields_filter} for r in body["data"]]

    def get_pages(self) -> Iterator[RepoListPage]:
        # base with trailing slash, path without leading slash for urljoin
        url: str = urljoin(self.url, self.REPO_LIST_PATH)

        response = self.page_request(url, self.query_params)

        while True:
            page_results = self.results_simplified(response.json())

            yield page_results

            assert len(response.links) > 0, "API changed: no Link header found"
            if "next" in response.links:
                url = response.links["next"]["url"]
            else:
                # last page
                break

            response = self.page_request(url, {})

    def get_origins_from_page(self, page: RepoListPage) -> Iterator[ListedOrigin]:
        """Convert a page of Gitea repositories into a list of ListedOrigins.

        """
        assert self.lister_obj.id is not None

        for repo in page:
            last_update = iso8601.parse_date(repo["updated_at"])

            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                url=repo["clone_url"],
                visit_type="git",
                last_update=last_update,
            )
