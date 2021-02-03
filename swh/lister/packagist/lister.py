# Copyright (C) 2019-2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Any, Dict, Iterator, List, Optional

import iso8601
import requests

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from .. import USER_AGENT
from ..pattern import CredentialsType, Lister

logger = logging.getLogger(__name__)

PackagistPageType = List[str]


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
    efficient on the Packagist side (no dymamic queries).
    Furthermore, subsequent listing will send the "If-Modified-Since" HTTP
    header to only retrieve packages metadata updated since the previous listing
    operation in order to save bandwidth and return only origins which might have
    new released versions.
    """

    LISTER_NAME = "Packagist"
    PACKAGIST_PACKAGES_LIST_URL = "https://packagist.org/packages/list.json"
    PACKAGIST_REPO_BASE_URL = "https://repo.packagist.org/p"

    def __init__(
        self, scheduler: SchedulerInterface, credentials: CredentialsType = None,
    ):
        super().__init__(
            scheduler=scheduler,
            url=self.PACKAGIST_PACKAGES_LIST_URL,
            instance="packagist",
            credentials=credentials,
        )

        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/json", "User-Agent": USER_AGENT}
        )
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

    def api_request(self, url: str) -> Any:
        logger.debug("Fetching URL %s", url)

        response = self.session.get(url)

        if response.status_code not in (200, 304):
            logger.warning(
                "Unexpected HTTP status code %s on %s: %s",
                response.status_code,
                response.url,
                response.content,
            )

        response.raise_for_status()

        # response is empty when status code is 304
        return response.json() if response.status_code == 200 else {}

    def get_pages(self) -> Iterator[PackagistPageType]:
        """
        Yield a single page listing all Packagist projects.
        """
        yield self.api_request(self.PACKAGIST_PACKAGES_LIST_URL)["packageNames"]

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
                metadata = self.api_request(
                    f"{self.PACKAGIST_REPO_BASE_URL}/{package_name}.json"
                )
                if not metadata.get("packages", {}):
                    # package metadata not updated since last listing
                    continue
                if package_name not in metadata["packages"]:
                    # missing package metadata in response
                    continue
                versions_info = metadata["packages"][package_name].values()
            except requests.exceptions.HTTPError:
                # error when getting package metadata (usually 404 when a
                # package has been removed), skip it and process next package
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
                dist_time = iso8601.parse_date(dist_time_str)
                if last_update is None or dist_time > last_update:
                    last_update = dist_time

            # skip package with already seen origin url or with missing required info
            if visit_type is None or origin_url is None or origin_url in origin_urls:
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
