# Copyright (C) 2022 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict, Iterator, List, Optional, Set, Type
from urllib.error import HTTPError
from urllib.parse import urljoin

import repomd

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import Lister

logger = logging.getLogger(__name__)


Release = int
Edition = str
PkgName = str
PkgVersion = str
FedoraOrigin = str
FedoraPageType = Type[repomd.Repo]
"""Each page is a list of packages from a given Fedora (release, edition) pair"""


def get_editions(release: Release) -> List[Edition]:
    """Get list of editions for a given release."""
    # Ignore dirs that don't contain .rpm files:
    # Docker,CloudImages,Atomic*,Spins,Live,Cloud_Atomic,Silverblue

    if release < 20:
        return ["Everything", "Fedora"]
    elif release < 28:
        return ["Everything", "Server", "Workstation"]
    else:
        return ["Everything", "Server", "Workstation", "Modular"]


def get_last_modified(pkg: repomd.Package) -> datetime:
    """Get timezone aware last modified time in UTC from RPM package metadata."""
    ts = pkg._element.find("common:time", namespaces=repomd._ns).get("build")
    return datetime.utcfromtimestamp(int(ts)).replace(tzinfo=timezone.utc)


def get_checksums(pkg: repomd.Package) -> Dict[str, str]:
    """Get checksums associated to rpm archive."""
    cs = pkg._element.find("common:checksum", namespaces=repomd._ns)
    cs_type = cs.get("type")
    if cs_type == "sha":
        cs_type = "sha1"
    return {cs_type: cs.text}


@dataclass
class FedoraListerState:
    """State of Fedora lister"""

    package_versions: Dict[PkgName, Set[PkgVersion]] = field(default_factory=dict)
    """Dictionary mapping a package name to all the versions found during
    last listing"""


class FedoraLister(Lister[FedoraListerState, FedoraPageType]):
    """
    List source packages for given Fedora releases.

    The lister will create a snapshot for each package name from all its
    available versions.

    If a package snapshot is different from the last listing operation,
    it will be sent to the scheduler that will create a loading task
    to archive newly found source code.

    Args:
        scheduler: instance of SchedulerInterface
        url: fedora package archives mirror URL
        releases: list of fedora releases to process
    """

    LISTER_NAME = "fedora"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        instance: str = "fedora",
        url: str = "https://archives.fedoraproject.org/pub/archive/fedora/linux/releases/",
        releases: List[Release] = [34, 35, 36],
        max_origins_per_page: Optional[int] = None,
        max_pages: Optional[int] = None,
        enable_origins: bool = True,
    ):
        super().__init__(
            scheduler=scheduler,
            url=url,
            instance=instance,
            credentials={},
            max_origins_per_page=max_origins_per_page,
            max_pages=max_pages,
            enable_origins=enable_origins,
        )

        self.releases = releases

        self.listed_origins: Dict[FedoraOrigin, ListedOrigin] = {}
        "will hold all listed origins info"
        self.origins_to_send: Set[FedoraOrigin] = set()
        "will hold updated origins since last listing"
        self.package_versions: Dict[PkgName, Set[PkgVersion]] = {}
        "will contain the lister state after a call to run"
        self.last_page = False

    def state_from_dict(self, d: Dict[str, Any]) -> FedoraListerState:
        return FedoraListerState(package_versions={k: set(v) for k, v in d.items()})

    def state_to_dict(self, state: FedoraListerState) -> Dict[str, Any]:
        return {k: list(v) for k, v in state.package_versions.items()}

    def page_request(self, release: Release, edition: Edition) -> FedoraPageType:
        """Return parsed packages for a given fedora release."""
        index_url = urljoin(
            self.url,
            f"{release}/{edition}/source/SRPMS/"
            if release < 24
            else f"{release}/{edition}/source/tree/",
        )

        repo = repomd.load(index_url)  # throws error if no repomd.xml is not found
        self.last_page = (
            release == self.releases[-1] and edition == get_editions(release)[-1]
        )

        logger.debug(
            "Fetched metadata from url: %s, found %d packages", index_url, len(repo)
        )
        # TODO: Extract more fields like "provides" and "requires" from *primary.xml
        # as extrinsic metadata using the pkg._element.findtext method
        return repo

    def get_pages(self) -> Iterator[FedoraPageType]:
        """Return an iterator on parsed fedora packages, one page per (release, edition) pair"""

        for release in self.releases:
            for edition in get_editions(release):
                logger.debug("Listing fedora release %s edition %s", release, edition)
                self.current_release = release
                self.current_edition = edition
                try:
                    yield self.page_request(release, edition)
                except HTTPError as http_error:
                    if http_error.getcode() == 404:
                        logger.debug(
                            "No packages metadata found for fedora release %s edition %s",
                            release,
                            edition,
                        )
                        continue
                    raise

    def origin_url_for_package(self, package_name: PkgName) -> FedoraOrigin:
        """Return the origin url for the given package"""
        return f"https://src.fedoraproject.org/rpms/{package_name}"

    def get_origins_from_page(self, page: FedoraPageType) -> Iterator[ListedOrigin]:
        """Convert a page of fedora package sources into an iterator of ListedOrigin."""
        assert self.lister_obj.id is not None

        origins_to_send = set()

        # iterate on each package's metadata
        for pkg_metadata in page:
            # extract package metadata
            package_name = pkg_metadata.name
            package_version = pkg_metadata.vr
            package_version_split = package_version.split(".")
            if package_version_split[-1].startswith("fc"):
                # remove trailing ".fcXY" in version for the rpm loader to avoid
                # creating multiple releases targeting same directory
                package_version = ".".join(package_version_split[:-1])

            package_build_time = get_last_modified(pkg_metadata)
            package_download_path = pkg_metadata.location

            # build origin url
            origin_url = self.origin_url_for_package(package_name)
            # create package version key as expected by the fedora (rpm) loader
            package_version_key = (
                f"fedora{self.current_release}/{self.current_edition}/"
                f"{package_version}"
            ).lower()

            # this is the first time a package is listed
            if origin_url not in self.listed_origins:
                # create a ListedOrigin object for it that can be later
                # updated with new package versions info
                self.listed_origins[origin_url] = ListedOrigin(
                    lister_id=self.lister_obj.id,
                    url=origin_url,
                    visit_type="rpm",
                    extra_loader_arguments={"packages": {}},
                    last_update=package_build_time,
                )

                # init set that will contain all listed package versions
                self.package_versions[package_name] = set()

            # origin will be yielded at the end of that method
            origins_to_send.add(origin_url)

            # update package metadata in parameter that will be provided
            # to the rpm loader
            self.listed_origins[origin_url].extra_loader_arguments["packages"][
                package_version_key
            ] = {
                "name": package_name,
                "version": package_version,
                "url": urljoin(page.baseurl, package_download_path),
                "buildTime": package_build_time.isoformat(),
                "checksums": get_checksums(pkg_metadata),
            }

            last_update = self.listed_origins[origin_url].last_update
            if last_update is not None and package_build_time > last_update:
                self.listed_origins[origin_url].last_update = package_build_time

            # add package version key to the set of found versions
            self.package_versions[package_name].add(package_version_key)

            # package has already been listed during a previous listing process
            if package_name in self.state.package_versions:
                new_versions = (
                    self.package_versions[package_name]
                    - self.state.package_versions[package_name]
                )
                # no new versions so far, no need to send the origin to the scheduler
                if not new_versions:
                    origins_to_send.remove(origin_url)

        logger.debug(
            "Found %s packages to update (new ones or packages with new versions).",
            len(origins_to_send),
        )
        logger.debug(
            "Current total number of listed packages is equal to %s.",
            len(self.listed_origins),
        )

        # yield from origins_to_send.values()
        self.origins_to_send.update(origins_to_send)

        if self.last_page:
            # yield listed origins when all fedora releases and editions processed
            yield from [
                self.listed_origins[origin_url] for origin_url in self.origins_to_send
            ]

    def finalize(self):
        # set mapping between listed package names and versions as lister state
        self.state.package_versions = self.package_versions
        self.updated = len(self.listed_origins) > 0
