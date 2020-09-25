# Copyright (C) 2018-2020 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import re
from typing import Any, Dict, List, MutableMapping, Optional, Tuple

from requests import Response
from urllib3.util import parse_url

from ..core.page_by_page_lister import PageByPageHttpLister
from .models import GiteaModel


class GiteaLister(PageByPageHttpLister):
    # Template path expecting an integer that represents the page id
    PATH_TEMPLATE = "repos/search?page=%d&sort=id"
    DEFAULT_URL = "https://try.gitea.io/api/v1/"
    MODEL = GiteaModel
    LISTER_NAME = "gitea"

    def __init__(
        self, url=None, instance=None, override_config=None, order="asc", limit=3
    ):
        super().__init__(url=url, override_config=override_config)
        if instance is None:
            instance = parse_url(self.url).host
        self.instance = instance
        self.PATH_TEMPLATE = "%s&order=%s&limit=%s" % (
            self.PATH_TEMPLATE,
            order,
            limit,
        )

    def get_model_from_repo(self, repo: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "instance": self.instance,
            "uid": f'{self.instance}/{repo["id"]}',
            "name": repo["name"],
            "full_name": repo["full_name"],
            "html_url": repo["html_url"],
            "origin_url": repo["clone_url"],
            "origin_type": "git",
        }

    def get_next_target_from_response(self, response: Response) -> Optional[int]:
        """Determine the next page identifier.

        """
        if "next" in response.links:
            next_url = response.links["next"]["url"]
            return self.get_page_from_url(next_url)
        return None

    def get_page_from_url(self, url: str) -> int:
        page_re = re.compile(r"^.*/search\?.*page=(\d+)")
        return int(page_re.match(url).group(1))  # type: ignore

    def transport_response_simplified(self, response: Response) -> List[Dict[str, Any]]:
        repos = response.json()["data"]
        return [self.get_model_from_repo(repo) for repo in repos]

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
            self._get_int(h, "x-total-count"),
            int(self.get_page_from_url(response.links["last"]["url"])),
            self._get_int(h, "x-per-page"),
        )

    def _get_int(self, headers: MutableMapping[str, Any], key: str) -> Optional[int]:
        _val = headers.get(key)
        if _val:
            return int(_val)
        return None

    def run(self, min_bound=1, max_bound=None, check_existence=False):
        return super().run(min_bound, max_bound, check_existence)
