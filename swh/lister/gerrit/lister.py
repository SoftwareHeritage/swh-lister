# Copyright (C) 2026  The Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json
import logging
from typing import Dict, Iterator, List, Optional, Union

from requests import HTTPError

from swh.lister.pattern import CredentialsType, StatelessLister
from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

logger = logging.getLogger(__name__)

GerritProjects = List[str]


class GerritLister(StatelessLister[GerritProjects]):
    """Lister class for Gerrit instances.

    This lister uses the Gerrit REST API projects endpoint
    https://gerrit-review.googlesource.com/Documentation/rest-api-projects.html
    """

    LISTER_NAME = "gerrit"

    LIMITs = ("all", "", 1000, 100, 10, 1)

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: Optional[str] = None,
        instance: Optional[str] = None,
        credentials: Optional[CredentialsType] = None,
        max_origins_per_page: Optional[int] = None,
        max_pages: Optional[int] = None,
        enable_origins: bool = True,
    ):
        """Lister class for Gerrit repositories."""
        super().__init__(
            scheduler=scheduler,
            url=url,
            instance=instance,
            credentials=credentials,
            max_origins_per_page=max_origins_per_page,
            max_pages=max_pages,
            enable_origins=enable_origins,
        )

        self.session.headers.update({"Accept": "application/json"})

        self.url = self.url.rstrip("/") + "/"

        self.api_url = self.url + "projects/"

    def api_request(self, query: str, more: str) -> Optional[Dict]:
        url = f"{self.api_url}{query}{more}"
        response = self.http_request(url)
        text = response.text
        text = text.strip()
        # Remove Cross Site Script Inclusion (XSSI) prevention prefix
        # https://gerrit-review.googlesource.com/Documentation/rest-api.html#output
        text = text.removeprefix(")]}'")
        text = text.strip()
        try:
            projects = json.loads(text)
        except json.JSONDecodeError:
            return None
        if isinstance(projects, dict):
            return projects
        else:
            return None

    def get_pages_limit(self, limit: Union[str, int]) -> Iterator[GerritProjects]:
        if isinstance(limit, int):
            query = f"{limit=}"
        else:
            query = limit
        sep = "&" if query else "?"
        query = f"?{query}" if query else ""
        start = 0
        while True:
            more = f"{sep}{start=}" if start else ""
            projects = self.api_request(query, more)
            if projects is None:
                raise ValueError
            else:
                yield list(projects)
                count = len(projects)
                _, info = projects.popitem()
                if info.get("_more_projects", False) is True:
                    start += count
                else:
                    break

    def get_pages(self) -> Iterator[GerritProjects]:
        """Generate git 'project' URLs found on the current Gerrit server."""

        # Some instances do not allow the all option to be enabled
        # Maybe some instances have limit requirements too?
        for limit in self.LIMITs:
            try:
                yield from self.get_pages_limit(limit)
                break
            except (ValueError, HTTPError):
                continue

    def get_origins_from_page(self, projects: GerritProjects) -> Iterator[ListedOrigin]:
        """Convert a list of Gerrit repositories into a list of ListedOrigins."""
        assert self.lister_obj.id is not None

        for project in projects:
            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                url=self.url + project,
                visit_type="git",
            )
