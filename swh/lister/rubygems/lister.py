# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging
from typing import Iterator, List, Optional, Text

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, StatelessLister

logger = logging.getLogger(__name__)

# Aliasing the page results returned by `get_pages` method from the lister.
RubyGemsListerPage = Text


class RubyGemsLister(StatelessLister[RubyGemsListerPage]):
    """Lister for RubyGems.org, the Ruby community’s gem hosting service."""

    LISTER_NAME = "rubygems"
    VISIT_TYPE = "rubygems"
    INSTANCE = "rubygems"

    INDEX_URL = "https://rubygems.org/versions"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        credentials: Optional[CredentialsType] = None,
    ):
        super().__init__(
            scheduler=scheduler,
            credentials=credentials,
            instance=self.INSTANCE,
            url=self.INDEX_URL,
        )

    def get_pages(self) -> Iterator[RubyGemsListerPage]:
        """Yield an iterator which returns 'page'

        It uses the index file located at `https://rubygems.org/versions`
        to get a list of package names. Each page returns an origin url based on
        the following pattern::

            https://rubygems.org/gems/{pkgname}

        """

        package_names: List[str] = []
        response = self.http_request(url=self.url)
        data = response.content.decode()

        # remove the first 3 lines (file headers + first package named '-')
        for line in data.splitlines()[3:]:
            package_names.append(line.split(" ")[0])

        # Remove duplicates
        package_names_set: List[str] = list(set(package_names))

        for pkgname in package_names_set:
            yield f"https://rubygems.org/gems/{pkgname}"

    def get_origins_from_page(self, page: RubyGemsListerPage) -> Iterator[ListedOrigin]:
        """Iterate on all pages and yield ListedOrigin instances."""
        assert self.lister_obj.id is not None

        yield ListedOrigin(
            lister_id=self.lister_obj.id,
            visit_type=self.VISIT_TYPE,
            url=page,
            last_update=None,
        )
