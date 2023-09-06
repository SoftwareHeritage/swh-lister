# Copyright (C) 2022-2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging
from typing import Iterator, List, Optional

import iso8601
from requests.exceptions import HTTPError

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, StatelessLister

logger = logging.getLogger(__name__)

# Aliasing the page results returned by `get_pages` method from the lister.
PubDevListerPage = List[str]


class PubDevLister(StatelessLister[PubDevListerPage]):
    """List pub.dev (Dart, Flutter) origins."""

    LISTER_NAME = "pubdev"
    VISIT_TYPE = "pubdev"
    INSTANCE = "pubdev"

    BASE_URL = "https://pub.dev/"
    PACKAGE_NAMES_URL_PATTERN = "{base_url}api/package-names"
    PACKAGE_INFO_URL_PATTERN = "{base_url}api/packages/{pkgname}"
    ORIGIN_URL_PATTERN = "{base_url}packages/{pkgname}"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: str = BASE_URL,
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

    def get_pages(self) -> Iterator[PubDevListerPage]:
        """Yield an iterator which returns 'page'

        It uses the api provided by https://pub.dev/api/ to find Dart and Flutter package
        origins.

        The http api call get "{base_url}package-names" to retrieve a sorted list
        of all package names.

        There is only one page that list all origins url based on "{base_url}packages/{pkgname}"
        """
        response = self.http_request(
            url=self.PACKAGE_NAMES_URL_PATTERN.format(base_url=self.url)
        )
        yield response.json()["packages"]

    def get_origins_from_page(self, page: PubDevListerPage) -> Iterator[ListedOrigin]:
        """Iterate on all pages and yield ListedOrigin instances."""
        assert self.lister_obj.id is not None

        for pkgname in page:
            package_info_url = self.PACKAGE_INFO_URL_PATTERN.format(
                base_url=self.url, pkgname=pkgname
            )
            try:
                response = self.http_request(url=package_info_url)
            except HTTPError:
                logger.warning(
                    "Failed to fetch metadata for package %s, skipping it from listing.",
                    pkgname,
                )
                continue
            package_metadata = response.json()
            package_versions = package_metadata["versions"]
            last_published = max(
                package_version["published"] for package_version in package_versions
            )
            origin_url = self.ORIGIN_URL_PATTERN.format(
                base_url=self.url, pkgname=pkgname
            )
            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                visit_type=self.VISIT_TYPE,
                url=origin_url,
                last_update=iso8601.parse_date(last_published),
            )
