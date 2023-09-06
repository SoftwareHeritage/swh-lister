# Copyright (C) 2022-2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging
from typing import Dict, Iterator, List, Optional

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, StatelessLister

logger = logging.getLogger(__name__)

# Aliasing the page results returned by `get_pages` method from the lister.
BowerListerPage = List[Dict[str, str]]


class BowerLister(StatelessLister[BowerListerPage]):
    """List Bower (Javascript package manager) origins."""

    LISTER_NAME = "bower"
    VISIT_TYPE = "git"  # Bower origins url are Git repositories
    INSTANCE = "bower"

    API_URL = "https://registry.bower.io/packages"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: str = API_URL,
        instance: str = INSTANCE,
        credentials: Optional[CredentialsType] = None,
        max_origins_per_page: Optional[int] = None,
        max_pages: Optional[int] = None,
        enable_origins: bool = True,
    ):
        super().__init__(
            scheduler=scheduler,
            credentials=credentials,
            instance=instance,
            url=url,
            max_origins_per_page=max_origins_per_page,
            max_pages=max_pages,
            enable_origins=enable_origins,
        )
        self.session.headers.update({"Accept": "application/json"})

    def get_pages(self) -> Iterator[BowerListerPage]:
        """Yield an iterator which returns 'page'

        It uses the api endpoint provided by `https://registry.bower.io/packages`
        to get a list of package names with an origin url that corresponds to Git
        repository.

        There is only one page that list all origins urls.
        """
        response = self.http_request(self.url)
        yield response.json()

    def get_origins_from_page(self, page: BowerListerPage) -> Iterator[ListedOrigin]:
        """Iterate on all pages and yield ListedOrigin instances."""
        assert self.lister_obj.id is not None

        for entry in page:
            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                visit_type=self.VISIT_TYPE,
                url=entry["url"],
                last_update=None,
            )
