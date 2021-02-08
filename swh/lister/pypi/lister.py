# Copyright (C) 2018-2021 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging
from typing import Iterator, List, Optional

from bs4 import BeautifulSoup
import requests

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from .. import USER_AGENT
from ..pattern import CredentialsType, StatelessLister

logger = logging.getLogger(__name__)

PackageListPage = List[str]


class PyPILister(StatelessLister[PackageListPage]):
    """List origins from PyPI.

    """

    LISTER_NAME = "pypi"
    INSTANCE = "pypi"  # As of today only the main pypi.org is used

    PACKAGE_LIST_URL = "https://pypi.org/simple/"
    PACKAGE_URL = "https://pypi.org/project/{package_name}/"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        credentials: Optional[CredentialsType] = None,
    ):
        super().__init__(
            scheduler=scheduler,
            url=self.PACKAGE_LIST_URL,
            instance=self.INSTANCE,
            credentials=credentials,
        )

        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/html", "User-Agent": USER_AGENT}
        )

    def get_pages(self) -> Iterator[PackageListPage]:

        response = self.session.get(self.PACKAGE_LIST_URL)

        response.raise_for_status()

        page = BeautifulSoup(response.content, features="html.parser")

        page_results = [p.text for p in page.find_all("a")]

        yield page_results

    def get_origins_from_page(
        self, packages_name: PackageListPage
    ) -> Iterator[ListedOrigin]:
        """Convert a page of PyPI repositories into a list of ListedOrigins."""
        assert self.lister_obj.id is not None

        for package_name in packages_name:
            package_url = self.PACKAGE_URL.format(package_name=package_name)

            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                url=package_url,
                visit_type="pypi",
                last_update=None,  # available on PyPI JSON API
            )
