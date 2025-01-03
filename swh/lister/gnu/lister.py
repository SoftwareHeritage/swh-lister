# Copyright (C) 2019-2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging
from typing import Any, Iterator, Mapping, Optional

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
    INSTANCE = "GNU"
    GNU_FTP_URL = "https://ftp.gnu.org"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: str = GNU_FTP_URL,
        instance: str = INSTANCE,
        credentials: CredentialsType = None,
        max_origins_per_page: Optional[int] = None,
        max_pages: Optional[int] = None,
        enable_origins: bool = True,
    ):
        super().__init__(
            scheduler=scheduler,
            url=url,
            instance=instance,
            credentials=credentials,
            max_origins_per_page=max_origins_per_page,
            max_pages=max_pages,
            enable_origins=enable_origins,
        )
        # no side-effect calls in constructor, if extra state is needed, as preconized
        # by the pattern docstring, this must happen in the get_pages method.
        self.gnu_tree: Optional[GNUTree] = None

    def get_pages(self) -> Iterator[GNUPageType]:
        """
        Yield a single page listing all GNU projects.
        """
        # first fetch the manifest to parse
        self.gnu_tree = GNUTree(f"{self.url}/tree.json.gz")
        yield self.gnu_tree.projects

    def get_origins_from_page(self, page: GNUPageType) -> Iterator[ListedOrigin]:
        """
        Iterate on all GNU projects and yield ListedOrigin instances.
        """
        assert self.lister_obj.id is not None
        assert self.gnu_tree is not None

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
