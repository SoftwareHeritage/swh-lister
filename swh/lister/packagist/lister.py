# Copyright (C) 2019-2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from random import shuffle
from typing import Any, Dict, Iterator, List, Optional

import iso8601
import requests
from tenacity import RetryError

from swh.core.utils import grouper
from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, Lister

logger = logging.getLogger(__name__)

PackagistPageType = List[str]


class NotModifiedSinceLastVisit(ValueError):
    """Exception raised when a package has seen no change since the last visit."""

    pass


@dataclass
class PackagistListerState:
    """State of Packagist lister"""

    last_listing_date: Optional[datetime] = None
    """Last date when packagist lister was executed"""


class PackagistLister(Lister[PackagistListerState, PackagistPageType]):
    """
    List all Packagist projects and send associated origins to scheduler.

    The lister queries the Packagist API, whose documentation can be found at
    https://packagist.org/apidoc.

    For each package, its metadata are retrieved using Packagist API endpoints
    whose responses are served from static files, which are guaranteed to be
    efficient on the Packagist side (no dynamic queries).
    Furthermore, subsequent listing will send the "If-Modified-Since" HTTP
    header to only retrieve packages metadata updated since the previous listing
    operation in order to save bandwidth and return only origins which might have
    new released versions.
    """

    LISTER_NAME = "Packagist"
    INSTANCE = "packagist"
    PACKAGIST_PACKAGES_LIST_URL = "https://packagist.org/packages/list.json"
    PACKAGIST_PACKAGE_URL_FORMATS = [
        # preferred, static, efficient on their side as it can be cached
        "https://repo.packagist.org/p2/{package_name}.json",
        # fallback from 1. ^ as it might contain development versions
        "https://repo.packagist.org/p2/{package_name}~dev.json",
        # composer v1 metadata, static, efficient but deprecated on their side.
        # From previous lister version: very few results but some still exists so ok to
        # check
        "https://repo.packagist.org/p/{package_name}.json",
        # dynamic, inefficient on packagist's end, should be used as a last resort
        "https://repo.packagist.org/packages/{package_name}.json",
    ]

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: str = PACKAGIST_PACKAGES_LIST_URL,
        instance: str = INSTANCE,
        credentials: CredentialsType = None,
        max_origins_per_page: Optional[int] = None,
        max_pages: Optional[int] = None,
        enable_origins: bool = True,
        record_batch_size: int = 1000,
    ):
        super().__init__(
            scheduler=scheduler,
            url=url,
            instance=instance,
            credentials=credentials,
            with_github_session=True,
            max_origins_per_page=max_origins_per_page,
            max_pages=max_pages,
            enable_origins=enable_origins,
            record_batch_size=record_batch_size,
        )

        self.session.headers.update({"Accept": "application/json"})
        self.listing_date = datetime.now().astimezone(tz=timezone.utc)

    def state_from_dict(self, d: Dict[str, Any]) -> PackagistListerState:
        last_listing_date = d.get("last_listing_date")
        if last_listing_date is not None:
            d["last_listing_date"] = iso8601.parse_date(last_listing_date)
        return PackagistListerState(**d)

    def state_to_dict(self, state: PackagistListerState) -> Dict[str, Any]:
        d: Dict[str, Optional[str]] = {"last_listing_date": None}
        last_listing_date = state.last_listing_date
        if last_listing_date is not None:
            d["last_listing_date"] = last_listing_date.isoformat()
        return d

    def api_request(self, url: str) -> Dict:
        """Execute api request to packagist server.

        Raise:
            NotModifiedSinceLastVisit: if the url returns a 304 response.

        Return:
            The json result in case of a 200, an empty response otherwise.

        """
        response = self.http_request(url)
        # response is empty when status code is 304
        status_code = response.status_code
        if status_code == 200:
            return response.json()
        elif status_code == 304:
            raise NotModifiedSinceLastVisit(url)
        else:
            return {}

    def get_pages(self) -> Iterator[PackagistPageType]:
        """Retrieve & randomize unique list of packages into pages of packages."""
        package_names = self.api_request(self.url)["packageNames"]
        shuffle(package_names)
        for page_packages in grouper(package_names, n=self.record_batch_size):
            yield page_packages

    def _get_metadata_from_page(
        self, package_url_format: str, package_name: str
    ) -> Optional[List[Dict]]:
        """Retrieve metadata from a package if any.

        Raise:
            NotModifiedSinceLastVisit: if the url returns a 304 response.

        Return:
            metadata from a package if any

        """
        try:
            metadata_url = package_url_format.format(package_name=package_name)
            metadata = self.api_request(metadata_url)
            packages = metadata.get("packages", {})
            format_json = metadata.get("minified")
            if not packages:
                # package metadata not updated since last listing
                return None
            package_info = packages.get(package_name)
            if package_info is None:
                # missing package metadata in response
                return None
            logger.debug(
                "package-name: %s, package-info: %s", package_name, package_info
            )
            if format_json == "composer/2.0":  # /p2/ output
                # In that format, the package info is a list of dict for each package
                # version
                return package_info
            else:
                # Otherwise, /p/, /packages/ urls returns a dict output
                return package_info.values()
        except requests.HTTPError:
            # error when getting package metadata (usually 404 when a package has
            # been removed), skip it and process next package
            return None

    def _get_metadata_for_package(self, package_name: str) -> Optional[List[Dict]]:
        """Tentatively retrieve metadata information from a package name.

        This tries out in order the following pages:
        - /p2/{package}.json: static and performant (on packagist's side) url.
        - /p2/{package}~dev.json: static, performant for development package url.
        - /packages/{package}.json: costly (for packagist's side) url

        If nothing is found in all urls, a None result is returned.

        Raise:
            NotModifiedSinceLastVisit: if the url returns a 304 response.

        Return:
            Metadata information on the package name if any.

        """
        for package_url_format in self.PACKAGIST_PACKAGE_URL_FORMATS:
            meta_info = self._get_metadata_from_page(package_url_format, package_name)
            # If information, return it immediately, otherwise fallback to the next
            if meta_info:
                return meta_info

        return None

    def get_origins_from_page(self, page: PackagistPageType) -> Iterator[ListedOrigin]:
        """
        Iterate on all Packagist projects and yield ListedOrigin instances.
        """
        assert self.lister_obj.id is not None

        # save some bandwidth by only getting packages metadata updated since
        # last listing
        if self.state.last_listing_date is not None:
            if_modified_since = self.state.last_listing_date.strftime(
                "%a, %d %b %Y %H:%M:%S GMT"
            )
            self.session.headers["If-Modified-Since"] = if_modified_since

        # to ensure origins will not be listed multiple times
        origin_urls = set()

        for package_name in page:
            try:
                versions_info = self._get_metadata_for_package(package_name)
            except NotModifiedSinceLastVisit:
                # Package was not modified server side since the last visit, we skip it
                continue

            if versions_info is None:
                # No info on package, we skip it
                continue

            origin_url = None
            visit_type = None
            last_update = None

            # extract origin url for package, vcs type and latest release date
            for version_info in versions_info:
                origin_url = version_info.get("source", {}).get("url", "")
                if not origin_url:
                    continue
                # can be git, hg or svn
                visit_type = version_info.get("source", {}).get("type", "")
                dist_time_str = version_info.get("time", "")
                if not dist_time_str:
                    continue
                try:
                    dist_time = iso8601.parse_date(dist_time_str)
                except iso8601.iso8601.ParseError:
                    continue
                if last_update is None or dist_time > last_update:
                    last_update = dist_time

            # skip package with already seen origin url or with missing required info
            if visit_type is None or origin_url is None or origin_url in origin_urls:
                continue

            if visit_type == "git":
                # Non-github urls will be returned as is, github ones will be canonical
                # ones
                assert self.github_session is not None
                try:
                    origin_url = (
                        self.github_session.get_canonical_url(origin_url) or origin_url
                    )
                except (requests.exceptions.ConnectionError, RetryError):
                    # server hangs up, let's ignore it for now
                    # that might not happen later on
                    continue

            # bitbucket closed its mercurial hosting service, those origins can not be
            # loaded into the archive anymore
            if visit_type == "hg" and origin_url.startswith("https://bitbucket.org/"):
                continue

            origin_urls.add(origin_url)

            logger.debug(
                "Found package %s last updated on %s", package_name, last_update
            )

            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                url=origin_url,
                visit_type=visit_type,
                last_update=last_update,
            )

    def finalize(self) -> None:
        self.state.last_listing_date = self.listing_date
        self.updated = True
