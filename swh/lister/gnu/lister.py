# Copyright (C) 2019-2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging
from typing import Any, Iterator, Mapping

import iso8601

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, StatelessLister
from .tree import GNUTree

logger = logging.getLogger(__name__)

GNUPageType = Mapping[str, Any]


class GNULister(StatelessLister[GNUPageType]):
    """
    List all GNU projects and associated artifacts.
    """

    LISTER_NAME = "GNU"
    GNU_FTP_URL = "https://ftp.gnu.org"

    def __init__(
        self, scheduler: SchedulerInterface, credentials: CredentialsType = None,
    ):
        super().__init__(
            scheduler=scheduler,
            url=self.GNU_FTP_URL,
            instance="GNU",
            credentials=credentials,
        )
        self.gnu_tree = GNUTree(f"{self.url}/tree.json.gz")

    def get_pages(self) -> Iterator[GNUPageType]:
        """
        Yield a single page listing all GNU projects.
        """
        yield self.gnu_tree.projects

    def get_origins_from_page(self, page: GNUPageType) -> Iterator[ListedOrigin]:
        """
        Iterate on all GNU projects and yield ListedOrigin instances.
        """
        assert self.lister_obj.id is not None

        artifacts = self.gnu_tree.artifacts

        for project_name, project_info in page.items():

            origin_url = project_info["url"]
            last_update = iso8601.parse_date(project_info["time_modified"])

            logger.debug("Found origin %s last updated on %s", origin_url, last_update)

            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                url=origin_url,
                visit_type="tar",
                last_update=last_update,
                extra_loader_arguments={"artifacts": artifacts[project_name]},
            )
