# Copyright (C) 2018-2019 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging
from typing import Iterator, List

import requests
import xmltodict

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from .. import USER_AGENT
from ..pattern import StatelessLister

logger = logging.getLogger(__name__)

PackageListPage = List[str]


class PyPILister(StatelessLister[PackageListPage]):
    """List origins from PyPI.

    """

    LISTER_NAME = "pypi"
    INSTANCE = "pypi"  # As of today only the main pypi.org is used

    PACKAGE_LIST_URL = "https://pypi.org/simple/"
    PACKAGE_URL = "https://pypi.org/project/{package_name}/"

    def __init__(self, scheduler: SchedulerInterface):
        super().__init__(
            scheduler=scheduler,
            credentials=None,
            url=self.PACKAGE_LIST_URL,
            instance=self.INSTANCE,
        )

        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/html", "User-Agent": USER_AGENT}
        )

    def get_pages(self) -> Iterator[PackageListPage]:

        response = self.session.get(self.PACKAGE_LIST_URL)

        response.raise_for_status()

        page_xmldict = xmltodict.parse(response.content)
        page_results = [p["#text"] for p in page_xmldict["html"]["body"]["a"]]

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
