# Copyright (C) 2022  The Software Heritage developers
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

from swh.lister.utils import throttling_retry
from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from .. import USER_AGENT
from ..pattern import CredentialsType, StatelessLister

logger = logging.getLogger(__name__)

# Aliasing page results returned by `GogsLister.get_pages` method
GogsListerPage = List[Dict[str, Any]]


class GogsLister(StatelessLister[GogsListerPage]):

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
            "page": 1,
        }

        self.api_token = api_token
        if self.api_token is None:

            if len(self.credentials) > 0:
                cred = random.choice(self.credentials)
                username = cred.get("username")
                self.api_token = cred["password"]
                logger.warning(
                    "Using authentication credentials from user %s", username or "???"
                )
            else:
                raise ValueError("No credentials or API token provided")

        self.max_page_limit = 2

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
                "Authorization": f"token {self.api_token}",
            }
        )

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
    def results_simplified(cls, body: Dict[str, GogsListerPage]) -> GogsListerPage:
        fields_filter = ["id", "clone_url", "updated_at"]
        return [{k: r[k] for k in fields_filter} for r in body["data"]]

    def get_pages(self) -> Iterator[GogsListerPage]:
        # base with trailing slash, path without leading slash for urljoin
        url = urljoin(self.url, self.REPO_LIST_PATH)
        response = self.page_request(url, self.query_params)

        while True:
            page_results = self.results_simplified(response.json())

            yield page_results

            assert len(response.links) > 0, "API changed: no Link header found"
            if "next" in response.links:
                url = response.links["next"]["url"]
            else:
                break

            response = self.page_request(url, {})

    def get_origins_from_page(self, page: GogsListerPage) -> Iterator[ListedOrigin]:
        """Convert a page of Gogs repositories into a list of ListedOrigins"""
        assert self.lister_obj.id is not None

        for repo in page:
            last_update = iso8601.parse_date(repo["updated_at"])

            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                visit_type=self.VISIT_TYPE,
                url=repo["clone_url"],
                last_update=last_update,
            )
