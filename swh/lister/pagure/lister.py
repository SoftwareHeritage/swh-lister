# Copyright (C) 2023 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from datetime import datetime, timezone
import logging
from typing import Any, Dict, Iterator, List, Optional

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, StatelessLister

logger = logging.getLogger(__name__)

ProjectsPage = List[Dict[str, Any]]


class PagureLister(StatelessLister[ProjectsPage]):
    """List git origins hosted on a Pagure forge."""

    LISTER_NAME = "pagure"

    API_PROJECTS_ENDPOINT = "/api/0/projects"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: Optional[str] = None,
        instance: Optional[str] = None,
        credentials: CredentialsType = None,
        max_origins_per_page: Optional[int] = None,
        max_pages: Optional[int] = None,
        enable_origins: bool = True,
        per_page=100,
    ):
        super().__init__(
            scheduler=scheduler,
            credentials=credentials,
            url=url.rstrip("/") if url else None,
            instance=instance,
            max_origins_per_page=max_origins_per_page,
            max_pages=max_pages,
            enable_origins=enable_origins,
        )

        self.per_page = per_page
        self.session.headers.update({"Accept": "application/json"})
        self.url = f"{self.url}{self.API_PROJECTS_ENDPOINT}"

    def get_pages(self) -> Iterator[ProjectsPage]:
        url_projects = self.url
        while url_projects:
            params = (
                {"per_page": self.per_page} if "per_page" not in url_projects else None
            )
            response = self.http_request(url_projects, params=params).json()
            yield response["projects"]
            url_projects = response["pagination"]["next"]

    def get_origins_from_page(self, projects: ProjectsPage) -> Iterator[ListedOrigin]:
        assert self.lister_obj.id is not None

        for project in projects:
            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                url=project["full_url"],
                visit_type="git",
                last_update=datetime.fromtimestamp(
                    int(project["date_modified"])
                ).replace(tzinfo=timezone.utc),
            )
