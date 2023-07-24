# Copyright (C) 2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging
from typing import Any, Dict, Iterator, List, Optional

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, StatelessLister

logger = logging.getLogger(__name__)

# Aliasing the page results returned by `get_pages` method from the lister.
ElmListerPage = List[Dict[str, Any]]


class ElmLister(StatelessLister[ElmListerPage]):
    """List Elm packages origins"""

    LISTER_NAME = "elm"
    VISIT_TYPE = "git"  # Elm origins url are Git repositories
    INSTANCE = "elm"

    SEARCH_URL = "https://package.elm-lang.org/search.json"

    REPO_URL_PATTERN = "https://github.com/{name}"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        credentials: Optional[CredentialsType] = None,
        max_origins_per_page: Optional[int] = None,
        max_pages: Optional[int] = None,
        enable_origins: bool = True,
    ):
        super().__init__(
            scheduler=scheduler,
            credentials=credentials,
            instance=self.INSTANCE,
            url=self.SEARCH_URL,
            max_origins_per_page=max_origins_per_page,
            max_pages=max_pages,
            enable_origins=enable_origins,
        )
        self.session.headers.update({"Accept": "application/json"})

    def get_pages(self) -> Iterator[ElmListerPage]:
        """Yield an iterator which returns 'page'

        It uses the unique Http api endpoint `https://package.elm-lang.org/search.json`
        to get a list of names corresponding to Github repository url suffixes.

        There is only one page that list all origins urls.
        """
        response = self.http_request(self.url)
        yield response.json()

    def get_origins_from_page(self, page: ElmListerPage) -> Iterator[ListedOrigin]:
        """Iterate on all pages and yield ListedOrigin instances"""
        assert self.lister_obj.id is not None

        for entry in page:
            name: str = entry["name"]
            repo_url: str = self.REPO_URL_PATTERN.format(name=name)

            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                visit_type=self.VISIT_TYPE,
                url=repo_url,
                last_update=None,
            )
