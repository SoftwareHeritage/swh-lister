# Copyright (C) 2017-2021 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


import bz2
from collections import defaultdict
from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime
import gzip
from itertools import product
import logging
import lzma
import os
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple
from urllib.parse import urljoin

from debian.deb822 import Sources
import requests

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from .. import USER_AGENT
from ..pattern import CredentialsType, Lister

logger = logging.getLogger(__name__)

decompressors: Dict[str, Callable[[Any], Any]] = {
    "gz": lambda f: gzip.GzipFile(fileobj=f),
    "bz2": bz2.BZ2File,
    "xz": lzma.LZMAFile,
}

Suite = str
Component = str
PkgName = str
PkgVersion = str
DebianOrigin = str
DebianPageType = Iterator[Sources]


@dataclass
class DebianListerState:
    """State of debian lister"""

    package_versions: Dict[PkgName, Set[PkgVersion]] = field(default_factory=dict)
    """Dictionary mapping a package name to all the versions found during
    last listing"""


class DebianLister(Lister[DebianListerState, DebianPageType]):
    """
    List source packages for a given debian or derivative distribution.

    The lister will create a snapshot for each package name from all its
    available versions.

    If a package snapshot is different from the last listing operation,
    it will be send to the scheduler that will create a loading task
    to archive newly found source code.

    Args:
        scheduler: instance of SchedulerInterface
        distribution: identifier of listed distribution (e.g. Debian, Ubuntu)
        mirror_url: debian package archives mirror URL
        suites: list of distribution suites to process
        components: list of package components to process
    """

    LISTER_NAME = "debian"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        distribution: str = "Debian",
        mirror_url: str = "http://deb.debian.org/debian/",
        suites: List[Suite] = ["stretch", "buster", "bullseye"],
        components: List[Component] = ["main", "contrib", "non-free"],
        credentials: Optional[CredentialsType] = None,
    ):
        super().__init__(
            scheduler=scheduler,
            url=mirror_url,
            instance=distribution,
            credentials=credentials,
        )

        # to ensure urljoin will produce valid Sources URL
        if not self.url.endswith("/"):
            self.url += "/"

        self.distribution = distribution
        self.suites = suites
        self.components = components

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

        # will hold all listed origins info
        self.listed_origins: Dict[DebianOrigin, ListedOrigin] = {}
        # will contain origin urls that have already been listed
        # in a previous page
        self.sent_origins: Set[DebianOrigin] = set()
        # will contain already listed package info that need to be sent
        # to the scheduler for update in the commit_page method
        self.origins_to_update: Dict[DebianOrigin, ListedOrigin] = {}
        # will contain the lister state after a call to run
        self.package_versions: Dict[PkgName, Set[PkgVersion]] = {}

    def state_from_dict(self, d: Dict[str, Any]) -> DebianListerState:
        return DebianListerState(package_versions={k: set(v) for k, v in d.items()})

    def state_to_dict(self, state: DebianListerState) -> Dict[str, Any]:
        return {k: list(v) for k, v in state.package_versions.items()}

    def debian_index_urls(
        self, suite: Suite, component: Component
    ) -> Iterator[Tuple[str, str]]:
        """Return an iterator on possible Sources file URLs as multiple compression
        formats can be used."""
        compression_exts = ("xz", "bz2", "gz")
        base_urls = [
            urljoin(self.url, f"dists/{suite}/{component}/source/Sources"),
            urljoin(self.url, f"dists/{suite}/updates/{component}/source/Sources"),
        ]
        for base_url, ext in product(base_urls, compression_exts):
            yield (f"{base_url}.{ext}", ext)
        yield (base_url, "")

    def page_request(self, suite: Suite, component: Component) -> DebianPageType:
        """Return parsed package Sources file for a given debian suite and component."""
        for url, compression in self.debian_index_urls(suite, component):
            response = requests.get(url, stream=True)
            logging.debug("Fetched URL: %s, status code: %s", url, response.status_code)
            if response.status_code == 200:
                last_modified = response.headers.get("Last-Modified")
                self.last_sources_update = (
                    parsedate_to_datetime(last_modified) if last_modified else None
                )
                decompressor = decompressors.get(compression)
                if decompressor:
                    data = decompressor(response.raw).readlines()
                else:
                    data = response.raw.readlines()
                break
        else:
            data = ""
            logger.debug("Could not retrieve sources index for %s/%s", suite, component)

        return Sources.iter_paragraphs(data)

    def get_pages(self) -> Iterator[DebianPageType]:
        """Return an iterator on parsed debian package Sources files, one per combination
        of debian suite and component."""
        for suite, component in product(self.suites, self.components):
            logger.debug(
                "Processing %s %s source packages info for %s component.",
                self.instance,
                suite,
                component,
            )
            self.current_suite = suite
            self.current_component = component
            yield self.page_request(suite, component)

    def origin_url_for_package(self, package_name: PkgName) -> DebianOrigin:
        """Return the origin url for the given package"""
        return f"deb://{self.instance}/packages/{package_name}"

    def get_origins_from_page(self, page: DebianPageType) -> Iterator[ListedOrigin]:
        """Convert a page of debian package sources into an iterator of ListedOrigin.

        Please note that the returned origins correspond to packages only
        listed for the first time in order to get an accurate origins counter
        in the statistics returned by the run method of the lister.

        Packages already listed in another page but with different versions will
        be put in cache by the method and updated ListedOrigin objects will
        be sent to the scheduler later in the commit_page method.

        Indeed as multiple debian suites can be processed, a similar set of
        package names can be listed for two different package source pages,
        only their version will differ, resulting in origins counted multiple
        times in lister statistics.
        """
        assert self.lister_obj.id is not None

        origins_to_send = {}
        self.origins_to_update = {}

        # iterate on each package source info
        for src_pkg in page:
            # gather package files info that will be used by the debian loader
            files: Dict[str, Dict[str, Any]] = defaultdict(dict)
            for field_ in src_pkg._multivalued_fields:
                if field_.startswith("checksums-"):
                    sum_name = field_[len("checksums-") :]
                else:
                    sum_name = "md5sum"
                if field_ in src_pkg:
                    for entry in src_pkg[field_]:
                        name = entry["name"]
                        files[name]["name"] = name
                        files[name]["size"] = int(entry["size"], 10)
                        files[name][sum_name] = entry[sum_name]
                        files[name]["uri"] = os.path.join(
                            self.url, src_pkg["Directory"], name
                        )

            # extract package name and version
            package_name = src_pkg["Package"]
            package_version = src_pkg["Version"]
            # build origin url
            origin_url = self.origin_url_for_package(package_name)

            # create package version key as expected by the debian loader
            package_version_key = (
                f"{self.current_suite}/{self.current_component}/{package_version}"
            )

            # this is the first time a package is listed
            if origin_url not in self.listed_origins:
                # create a ListedOrigin object for it that can be later
                # updated with new package versions info
                self.listed_origins[origin_url] = ListedOrigin(
                    lister_id=self.lister_obj.id,
                    url=origin_url,
                    visit_type="deb",
                    extra_loader_arguments={"packages": {}},
                    last_update=self.last_sources_update,
                )
                # origin will be yielded at the end of that method
                origins_to_send[origin_url] = self.listed_origins[origin_url]
                # init set that will contain all listed package versions
                self.package_versions[package_name] = set()

            # package has already been listed in a previous page or current page
            elif origin_url not in origins_to_send:
                # if package has been listed in a previous page, its new versions
                # will be added to its ListedOrigin object but the update will
                # be sent to the scheduler in the commit_page method
                self.origins_to_update[origin_url] = self.listed_origins[origin_url]

            # update package versions data in parameter that will be provided
            # to the debian loader
            self.listed_origins[origin_url].extra_loader_arguments["packages"].update(
                {
                    package_version_key: {
                        "name": package_name,
                        "version": package_version,
                        "files": files,
                    }
                }
            )

            if self.listed_origins[origin_url].last_update is None or (
                self.last_sources_update is not None
                and self.last_sources_update  # type: ignore
                > self.listed_origins[origin_url].last_update
            ):
                # update debian package last update if current processed sources index
                # has a greater modification date
                self.listed_origins[origin_url].last_update = self.last_sources_update

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
                    origins_to_send.pop(origin_url, None)
                    self.origins_to_update.pop(origin_url, None)
                # new versions found, ensure the origin will be sent to the scheduler
                elif origin_url not in self.sent_origins:
                    self.origins_to_update.pop(origin_url, None)
                    origins_to_send[origin_url] = self.listed_origins[origin_url]

        # update already counted origins with changes since last page
        self.sent_origins.update(origins_to_send.keys())

        logger.debug(
            "Found %s new packages, %s packages with new versions.",
            len(origins_to_send),
            len(self.origins_to_update),
        )
        logger.debug(
            "Current total number of listed packages is equal to %s.",
            len(self.listed_origins),
        )

        yield from origins_to_send.values()

    def get_origins_to_update(self) -> Iterator[ListedOrigin]:
        yield from self.origins_to_update.values()

    def commit_page(self, page: DebianPageType):
        """Send to scheduler already listed origins where new versions have been found
        in current page."""
        self.send_origins(self.get_origins_to_update())

    def finalize(self):
        # set mapping between listed package names and versions as lister state
        self.state.package_versions = self.package_versions
        self.updated = len(self.sent_origins) > 0
