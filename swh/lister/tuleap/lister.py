# Copyright (C) 2021 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging
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

RepoPage = Dict[str, Any]


class TuleapLister(StatelessLister[RepoPage]):
    """List origins from Tuleap.

    Tuleap provides SVN and Git repositories hosting.

    Tuleap API getting started:
    https://tuleap.net/doc/en/user-guide/integration/rest.html
    Tuleap API reference:
    https://tuleap.net/api/explorer/

    Using the API we first request a list of projects, and from there request their
    associated repositories individually. Everything is paginated, code uses throttling
    at the individual GET call level."""

    LISTER_NAME = "tuleap"

    REPO_LIST_PATH = "/api"
    REPO_GIT_PATH = "plugins/git/"
    REPO_SVN_PATH = "plugins/svn/"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: str,
        instance: Optional[str] = None,
        credentials: CredentialsType = None,
    ):
        super().__init__(
            scheduler=scheduler, credentials=credentials, url=url, instance=instance,
        )

        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/json", "User-Agent": USER_AGENT,}
        )

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
    def results_simplified(cls, url: str, repo_type: str, repo: RepoPage) -> RepoPage:
        if repo_type == "git":
            prefix_url = TuleapLister.REPO_GIT_PATH
        else:
            prefix_url = TuleapLister.REPO_SVN_PATH
        rep = {
            "project": repo["name"],
            "type": repo_type,
            "uri": urljoin(url, f"{prefix_url}{repo['path']}"),
            "last_update_date": repo["last_update_date"],
        }
        return rep

    def _get_repositories(self, url_repo) -> List[Dict[str, Any]]:
        ret = self.page_request(url_repo, {})
        reps_list = ret.json()["repositories"]
        limit = int(ret.headers["X-PAGINATION-LIMIT-MAX"])
        offset = int(ret.headers["X-PAGINATION-LIMIT"])
        size = int(ret.headers["X-PAGINATION-SIZE"])
        while offset < size:
            url_offset = url_repo + "?offset=" + str(offset) + "&limit=" + str(limit)
            ret = self.page_request(url_offset, {}).json()
            reps_list = reps_list + ret["repositories"]
            offset += limit
        return reps_list

    def get_pages(self) -> Iterator[RepoPage]:
        # base with trailing slash, path without leading slash for urljoin
        url_api: str = urljoin(self.url, self.REPO_LIST_PATH)
        url_projects = url_api + "/projects/"

        # Get the list of projects.
        response = self.page_request(url_projects, {})
        projects_list = response.json()
        limit = int(response.headers["X-PAGINATION-LIMIT-MAX"])
        offset = int(response.headers["X-PAGINATION-LIMIT"])
        size = int(response.headers["X-PAGINATION-SIZE"])
        while offset < size:
            url_offset = (
                url_projects + "?offset=" + str(offset) + "&limit=" + str(limit)
            )
            ret = self.page_request(url_offset, {}).json()
            projects_list = projects_list + ret
            offset += limit

        # Get list of repositories for each project.
        for p in projects_list:
            p_id = p["id"]

            # Fetch Git repositories for project
            url_git = url_projects + str(p_id) + "/git"
            repos = self._get_repositories(url_git)
            for repo in repos:
                yield self.results_simplified(url_api, "git", repo)

    def get_origins_from_page(self, page: RepoPage) -> Iterator[ListedOrigin]:
        """Convert a page of Tuleap repositories into a list of ListedOrigins.

        """
        assert self.lister_obj.id is not None

        yield ListedOrigin(
            lister_id=self.lister_obj.id,
            url=page["uri"],
            visit_type=page["type"],
            last_update=iso8601.parse_date(page["last_update_date"]),
        )
