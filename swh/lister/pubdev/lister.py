# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information
import logging
from typing import Any, Dict, Iterator, List, Optional

import iso8601
import requests
from requests.exceptions import HTTPError
from tenacity.before_sleep import before_sleep_log

from swh.lister.utils import throttling_retry
from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from .. import __version__
from ..pattern import CredentialsType, StatelessLister

# https://github.com/dart-lang/pub/blob/master/doc/repository-spec-v2.md#metadata-headers
USER_AGENT = (
    f"Software Heritage PubDev Lister v{__version__} "
    "(+https://www.softwareheritage.org/contact)"
)

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
        credentials: Optional[CredentialsType] = None,
    ):
        super().__init__(
            scheduler=scheduler,
            credentials=credentials,
            instance=self.INSTANCE,
            url=self.BASE_URL,
        )
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            }
        )

    @throttling_retry(before_sleep=before_sleep_log(logger, logging.WARNING))
    def page_request(self, url: str, params: Dict[str, Any]) -> requests.Response:

        logger.debug("Fetching URL %s with params %s", url, params)

        response = self.session.get(url, params=params)
        if response.status_code != 200:
            logger.warning(
                "Unexpected HTTP status code %s on %s: %s",
                response.status_code,
                response.url,
                response.content,
            )
        response.raise_for_status()

        return response

    def get_pages(self) -> Iterator[PubDevListerPage]:
        """Yield an iterator which returns 'page'

        It uses the api provided by https://pub.dev/api/ to find Dart and Flutter package
        origins.

        The http api call get "{base_url}package-names" to retrieve a sorted list
        of all package names.

        There is only one page that list all origins url based on "{base_url}packages/{pkgname}"
        """
        response = self.page_request(
            url=self.PACKAGE_NAMES_URL_PATTERN.format(base_url=self.url), params={}
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
                response = self.page_request(url=package_info_url, params={})
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
