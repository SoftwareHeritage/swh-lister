# Copyright (C) 2018-2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Any, Dict, List, Optional

from requests import Response

from swh.core import config
from swh.lister.core.indexing_lister import IndexingHttpLister
from swh.lister.npm.models import NpmModel
from swh.scheduler.utils import create_task_dict

DEFAULT_CONFIG = {
    "loading_task_policy": "recurring",
}


class NpmListerBase(IndexingHttpLister):
    """List packages available in the npm registry in a paginated way

    """

    MODEL = NpmModel
    LISTER_NAME = "npm"
    instance = "npm"

    def __init__(
        self, url="https://replicate.npmjs.com", per_page=1000, override_config=None
    ):
        super().__init__(url=url, override_config=override_config)
        self.config = config.merge_configs(DEFAULT_CONFIG, self.config)
        self.per_page = per_page + 1
        self.PATH_TEMPLATE += "&limit=%s" % self.per_page

    def get_model_from_repo(self, repo_name: str) -> Dict[str, str]:
        """(Override) Transform from npm package name to model

        """
        package_url = "https://www.npmjs.com/package/%s" % repo_name
        return {
            "uid": repo_name,
            "indexable": repo_name,
            "name": repo_name,
            "full_name": repo_name,
            "html_url": package_url,
            "origin_url": package_url,
            "origin_type": "npm",
        }

    def task_dict(self, origin_type: str, origin_url: str, **kwargs):
        """(Override) Return task dict for loading a npm package into the
        archive.

        This is overridden from the lister_base as more information is
        needed for the ingestion task creation.

        """
        task_type = "load-%s" % origin_type
        task_policy = self.config["loading_task_policy"]
        return create_task_dict(task_type, task_policy, url=origin_url)

    def request_headers(self) -> Dict[str, Any]:
        """(Override) Set requests headers to send when querying the npm
        registry.

        """
        headers = super().request_headers()
        headers["Accept"] = "application/json"
        return headers

    def string_pattern_check(self, inner: int, lower: int, upper: int = None):
        """ (Override) Inhibit the effect of that method as packages indices
        correspond to package names and thus do not respect any kind
        of fixed length string pattern

        """
        pass


class NpmLister(NpmListerBase):
    """List all packages available in the npm registry in a paginated way

    """

    PATH_TEMPLATE = '/_all_docs?startkey="%s"'

    def get_next_target_from_response(self, response: Response) -> Optional[str]:
        """(Override) Get next npm package name to continue the listing

        """
        repos = response.json()["rows"]
        return repos[-1]["id"] if len(repos) == self.per_page else None

    def transport_response_simplified(self, response: Response) -> List[Dict[str, str]]:
        """(Override) Transform npm registry response to list for model manipulation

        """
        repos = response.json()["rows"]
        if len(repos) == self.per_page:
            repos = repos[:-1]
        return [self.get_model_from_repo(repo["id"]) for repo in repos]


class NpmIncrementalLister(NpmListerBase):
    """List packages in the npm registry, updated since a specific
    update_seq value of the underlying CouchDB database, in a paginated way.

    """

    PATH_TEMPLATE = "/_changes?since=%s"

    @property
    def CONFIG_BASE_FILENAME(self):  # noqa: N802
        return "lister_npm_incremental"

    def get_next_target_from_response(self, response: Response) -> Optional[str]:
        """(Override) Get next npm package name to continue the listing.

        """
        repos = response.json()["results"]
        return repos[-1]["seq"] if len(repos) == self.per_page else None

    def transport_response_simplified(self, response: Response) -> List[Dict[str, str]]:
        """(Override) Transform npm registry response to list for model
        manipulation.

        """
        repos = response.json()["results"]
        if len(repos) == self.per_page:
            repos = repos[:-1]
        return [self.get_model_from_repo(repo["id"]) for repo in repos]

    def filter_before_inject(self, models_list: List[Dict[str, Any]]):
        """(Override) Filter out documents in the CouchDB database
        not related to a npm package.

        """
        models_filtered = []
        for model in models_list:
            package_name = model["name"]
            # document related to CouchDB internals
            if package_name.startswith("_design/"):
                continue
            models_filtered.append(model)
        return models_filtered

    def disable_deleted_repo_tasks(self, start, end, keep_these):
        """(Override) Disable the processing performed by that method as it is
        not relevant in this incremental lister context. It also raises an
        exception due to a different index type (int instead of str).

        """
        pass
