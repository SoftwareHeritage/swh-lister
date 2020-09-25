# Copyright (C) 2018-2019 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import time
from typing import Any, Dict, List, MutableMapping, Optional, Tuple, Union

from requests import Response
from urllib3.util import parse_url

from ..core.page_by_page_lister import PageByPageHttpLister
from .models import GitLabModel


class GitLabLister(PageByPageHttpLister):
    # Template path expecting an integer that represents the page id
    PATH_TEMPLATE = "/projects?page=%d&order_by=id"
    DEFAULT_URL = "https://gitlab.com/api/v4/"
    MODEL = GitLabModel
    LISTER_NAME = "gitlab"

    def __init__(
        self, url=None, instance=None, override_config=None, sort="asc", per_page=20
    ):
        super().__init__(url=url, override_config=override_config)
        if instance is None:
            instance = parse_url(self.url).host
        self.instance = instance
        self.PATH_TEMPLATE = "%s&sort=%s&per_page=%s" % (
            self.PATH_TEMPLATE,
            sort,
            per_page,
        )

    def uid(self, repo: Dict[str, Any]) -> str:
        return "%s/%s" % (self.instance, repo["path_with_namespace"])

    def get_model_from_repo(self, repo: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "instance": self.instance,
            "uid": self.uid(repo),
            "name": repo["name"],
            "full_name": repo["path_with_namespace"],
            "html_url": repo["web_url"],
            "origin_url": repo["http_url_to_repo"],
            "origin_type": "git",
        }

    def transport_quota_check(
        self, response: Response
    ) -> Tuple[bool, Union[int, float]]:
        """Deal with rate limit if any.

        """
        # not all gitlab instance have rate limit
        if "RateLimit-Remaining" in response.headers:
            reqs_remaining = int(response.headers["RateLimit-Remaining"])
            if response.status_code == 403 and reqs_remaining == 0:
                reset_at = int(response.headers["RateLimit-Reset"])
                delay = min(reset_at - time.time(), 3600)
                return True, delay
        return False, 0

    def _get_int(self, headers: MutableMapping[str, Any], key: str) -> Optional[int]:
        _val = headers.get(key)
        if _val:
            return int(_val)
        return None

    def get_next_target_from_response(self, response: Response) -> Optional[int]:
        """Determine the next page identifier.

        """
        return self._get_int(response.headers, "x-next-page")

    def get_pages_information(
        self,
    ) -> Tuple[Optional[int], Optional[int], Optional[int]]:
        """Determine pages information.

        """
        response = self.transport_head(identifier=1)  # type: ignore
        if not response.ok:
            raise ValueError(
                "Problem during information fetch: %s" % response.status_code
            )
        h = response.headers
        return (
            self._get_int(h, "x-total"),
            self._get_int(h, "x-total-pages"),
            self._get_int(h, "x-per-page"),
        )

    def transport_response_simplified(self, response: Response) -> List[Dict[str, Any]]:
        repos = response.json()
        return [self.get_model_from_repo(repo) for repo in repos]
