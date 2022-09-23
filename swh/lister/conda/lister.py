# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import bz2
from collections import defaultdict
import datetime
import json
import logging
from typing import Any, Dict, Iterator, List, Optional, Tuple

import iso8601

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, StatelessLister

logger = logging.getLogger(__name__)

# Aliasing the page results returned by `get_pages` method from the lister.
CondaListerPage = Tuple[str, Dict[str, Dict[str, Any]]]


class CondaLister(StatelessLister[CondaListerPage]):
    """List Conda (anaconda.com) origins."""

    LISTER_NAME = "conda"
    VISIT_TYPE = "conda"
    INSTANCE = "conda"
    BASE_REPO_URL = "https://repo.anaconda.com/pkgs"
    REPO_URL_PATTERN = "{url}/{channel}/{arch}/repodata.json.bz2"
    ORIGIN_URL_PATTERN = "https://anaconda.org/{channel}/{pkgname}"
    ARCHIVE_URL_PATTERN = "{url}/{channel}/{arch}/{filename}"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        credentials: Optional[CredentialsType] = None,
        url: str = BASE_REPO_URL,
        channel: str = "",
        archs: List = [],
    ):
        super().__init__(
            scheduler=scheduler,
            credentials=credentials,
            instance=self.INSTANCE,
            url=url,
        )
        self.channel: str = channel
        self.archs: List[str] = archs
        self.packages: Dict[str, Any] = defaultdict(dict)
        self.package_dates: Dict[str, Any] = defaultdict(list)

    def get_pages(self) -> Iterator[CondaListerPage]:
        """Yield an iterator which returns 'page'"""

        for arch in self.archs:
            repodata_url = self.REPO_URL_PATTERN.format(
                url=self.url, channel=self.channel, arch=arch
            )
            response = self.http_request(url=repodata_url)
            packages = json.loads(bz2.decompress(response.content))["packages"]
            yield (arch, packages)

    def get_origins_from_page(self, page: CondaListerPage) -> Iterator[ListedOrigin]:
        """Iterate on all pages and yield ListedOrigin instances."""
        assert self.lister_obj.id is not None
        arch, packages = page

        for filename, package_metadata in packages.items():
            artifact = {
                "filename": filename,
                "url": self.ARCHIVE_URL_PATTERN.format(
                    url=self.url,
                    channel=self.channel,
                    filename=filename,
                    arch=arch,
                ),
                "version": package_metadata["version"],
                "checksums": {},
            }

            for checksum in ("md5", "sha256"):
                if checksum in package_metadata:
                    artifact["checksums"][checksum] = package_metadata[checksum]

            version_key = (
                f"{arch}/{package_metadata['version']}-{package_metadata['build']}"
            )
            self.packages[package_metadata["name"]][version_key] = artifact

            package_date = None
            if "timestamp" in package_metadata:
                package_date = datetime.datetime.fromtimestamp(
                    package_metadata["timestamp"] / 1e3, datetime.timezone.utc
                )
            elif "date" in package_metadata:
                package_date = iso8601.parse_date(package_metadata["date"])

            last_update = None
            if package_date:
                artifact["date"] = package_date.isoformat()
                self.package_dates[package_metadata["name"]].append(package_date)
                last_update = max(self.package_dates[package_metadata["name"]])

            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                visit_type=self.VISIT_TYPE,
                url=self.ORIGIN_URL_PATTERN.format(
                    channel=self.channel, pkgname=package_metadata["name"]
                ),
                last_update=last_update,
                extra_loader_arguments={
                    "artifacts": self.packages[package_metadata["name"]],
                },
            )