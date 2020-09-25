# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging
from typing import Any, Dict, List

from requests import Response

from swh.lister.core.simple_lister import SimpleLister
from swh.lister.gnu.models import GNUModel
from swh.lister.gnu.tree import GNUTree
from swh.scheduler import utils

logger = logging.getLogger(__name__)


class GNULister(SimpleLister):
    MODEL = GNUModel
    LISTER_NAME = "gnu"
    instance = "gnu"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gnu_tree = GNUTree("https://ftp.gnu.org/tree.json.gz")

    def task_dict(self, origin_type, origin_url, **kwargs):
        """Return task format dict

        This is overridden from the lister_base as more information is
        needed for the ingestion task creation.

        This creates tasks with args and kwargs set, for example:

        .. code-block:: python

            args:
            kwargs: {
                'url': 'https://ftp.gnu.org/gnu/3dldf/',
                'artifacts': [{
                    'url': 'https://...',
                    'time': '2003-12-09T21:43:20+00:00',
                    'length': 128,
                    'version': '1.0.1',
                    'filename': 'something-1.0.1.tar.gz',
                },
                ...
                ]
            }

        """
        artifacts = self.gnu_tree.artifacts[origin_url]
        assert origin_type == "tar"
        return utils.create_task_dict(
            "load-archive-files",
            kwargs.get("policy", "oneshot"),
            url=origin_url,
            artifacts=artifacts,
            retries_left=3,
        )

    def safely_issue_request(self, identifier: int) -> None:
        """Bypass the implementation. It's now the GNUTree which deals with
        querying the gnu mirror.

        As an implementation detail, we cannot change simply the base
        SimpleLister as other implementation still uses it. This shall be part
        of another refactoring pass.

        """
        return None

    def list_packages(self, response: Response) -> List[Dict[str, Any]]:
        """List the actual gnu origins (package name) with their name, url and
           associated tarballs.

        Args:
            response: Unused

        Returns:
            List of packages name, url, last modification time::

                [
                    {
                        'name': '3dldf',
                        'url': 'https://ftp.gnu.org/gnu/3dldf/',
                        'time_modified': '2003-12-09T20:43:20+00:00'
                    },
                    {
                        'name': '8sync',
                        'url': 'https://ftp.gnu.org/gnu/8sync/',
                        'time_modified': '2016-12-06T02:37:10+00:00'
                    },
                    ...
                ]

        """
        return list(self.gnu_tree.projects.values())

    def get_model_from_repo(self, repo: Dict[str, Any]) -> Dict[str, Any]:
        """Transform from repository representation to model

        """
        return {
            "uid": repo["url"],
            "name": repo["name"],
            "full_name": repo["name"],
            "html_url": repo["url"],
            "origin_url": repo["url"],
            "time_last_updated": repo["time_modified"],
            "origin_type": "tar",
        }
