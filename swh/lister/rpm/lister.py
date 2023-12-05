# Copyright (C) 2022-2023 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from dataclasses import dataclass, field
from datetime import datetime, timezone
from itertools import product
import logging
from string import Template
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple
from urllib.parse import urljoin

import repomd
from typing_extensions import TypedDict

from swh.lister.pattern import CredentialsType
from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import Lister

logger = logging.getLogger(__name__)


Release = str
Component = str
PkgName = str
PkgVersion = str
RPMOrigin = str

RPMPageType = Optional[Tuple[Release, Component, repomd.Repo]]
"""Each page is a list of packages for a given (release, component) pair
from a Red Hat based distribution."""


class RPMSourceData(TypedDict):
    """Dictionary holding relevant data for listing RPM source packages.

    See content of the lister config directory to get examples of RPM
    source data for famous RedHat based distributions.
    """

    base_url: str
    """Base URL of a RPM repository"""
    releases: List[Release]
    """List of release identifiers for a Red Hat based distribution"""
    components: List[Component]
    """List of components for a Red Hat based distribution"""
    index_url_templates: List[str]
    """List of URL templates to discover source packages metadata, the
    following variables can be substituted in them: ``base_url``, ``release``
    and ``edition``, see :class:`string.Template` for more details about the
    format. The generated URLs must target directories containing a sub-directory
    named ``repodata``, which contains packages metadata, in order to be
    successfully processed by the lister."""


def _get_last_modified(pkg: repomd.Package) -> datetime:
    """Get timezone aware last modified time in UTC from RPM package metadata."""
    ts = pkg._element.find("common:time", namespaces=repomd._ns).get("build")
    return datetime.utcfromtimestamp(int(ts)).replace(tzinfo=timezone.utc)


def _get_checksums(pkg: repomd.Package) -> Dict[str, str]:
    """Get checksums associated to rpm archive."""
    cs = pkg._element.find("common:checksum", namespaces=repomd._ns)
    cs_type = cs.get("type")
    if cs_type == "sha":
        cs_type = "sha1"
    return {cs_type: cs.text}


@dataclass
class RPMListerState:
    """State of RPM lister"""

    package_versions: Dict[PkgName, Set[PkgVersion]] = field(default_factory=dict)
    """Dictionary mapping a package name to all the versions found during
    last listing"""


class RPMLister(Lister[RPMListerState, RPMPageType]):
    """
    List source packages for a Red Hat based linux distribution.

    The lister creates a snapshot for each package from all its available versions.

    In incremental mode, only packages with different snapshot since the last listing
    operation will be sent to the scheduler that will create loading tasks to archive
    newly found source code.

    Args:
        scheduler: instance of SchedulerInterface
        url: Red Hat based distribution info URL
        instance: name of Red Hat based distribution
        rpm_src_data: list of dictionaries holding data required to list RPM source packages,
            see examples in the config directory.
        incremental: if :const:`True`, only packages with new versions are sent to the
            scheduler when relisting
    """

    LISTER_NAME = "rpm"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: str,
        instance: str,
        rpm_src_data: List[RPMSourceData],
        incremental: bool = False,
        max_origins_per_page: Optional[int] = None,
        max_pages: Optional[int] = None,
        enable_origins: bool = True,
        credentials: Optional[CredentialsType] = None,
    ):
        super().__init__(
            scheduler=scheduler,
            url=url,
            instance=instance,
            credentials=credentials,
            max_origins_per_page=max_origins_per_page,
            max_pages=max_pages,
            enable_origins=enable_origins,
        )

        self.rpm_src_data = rpm_src_data
        self.incremental = incremental

        self.listed_origins: Dict[RPMOrigin, ListedOrigin] = {}
        self.origins_to_send: Set[RPMOrigin] = set()
        self.package_versions: Dict[PkgName, Set[PkgVersion]] = {}

    def state_from_dict(self, d: Dict[str, Any]) -> RPMListerState:
        return RPMListerState(package_versions={k: set(v) for k, v in d.items()})

    def state_to_dict(self, state: RPMListerState) -> Dict[str, Any]:
        return {k: list(v) for k, v in state.package_versions.items()}

    def repo_request(
        self,
        index_url_template: Template,
        base_url: str,
        release: Release,
        component: Component,
    ) -> Optional[RPMPageType]:
        """Return parsed packages for a given distribution release and component."""

        index_url = index_url_template.substitute(
            base_url=base_url.rstrip("/"), release=release, component=component
        )

        try:
            repo = repomd.load(index_url)  # throws error if no repomd.xml is not found
        except Exception:
            logger.debug("Repository metadata not found at URL %s", index_url)
            return None
        else:
            logger.debug(
                "Fetched metadata from url: %s, found %d packages", index_url, len(repo)
            )
            return repo

    def get_pages(self) -> Iterator[RPMPageType]:
        """Return an iterator on parsed rpm packages, one page per (release, component) pair."""
        for rpm_src_data in self.rpm_src_data:
            index_url_templates = [
                Template(index_url_template)
                for index_url_template in rpm_src_data["index_url_templates"]
            ]
            # try all possible package repository URLs for each (release, component) pair
            for release, component, index_url_template in product(
                rpm_src_data["releases"],
                rpm_src_data["components"],
                index_url_templates,
            ):
                repo = self.repo_request(
                    index_url_template,
                    rpm_src_data["base_url"],
                    release,
                    component,
                )
                if repo is not None:
                    # valid package repository found, yield page
                    yield (release, component, repo)

        yield None

    def origin_url_for_package(self, package_name: PkgName) -> RPMOrigin:
        """Return the origin url for the given package."""
        # TODO: Use a better origin URL before deploying the lister to production
        # https://gitlab.softwareheritage.org/swh/devel/swh-model/-/issues/4632
        return f"rpm://{self.instance}/packages/{package_name}"

    def get_origins_from_page(self, page: RPMPageType) -> Iterator[ListedOrigin]:
        """Convert a page of rpm package sources into an iterator of ListedOrigin."""
        assert self.lister_obj.id is not None

        if page is None:
            # all pages processed, yield listed origins
            for origin_url in self.origins_to_send:
                yield self.listed_origins[origin_url]
            return

        release, component, repo = page

        logger.debug(
            "Listing %s release %s component %s from repository metadata located at %s",
            self.instance,
            release,
            component,
            repo.baseurl,
        )

        origins_to_send = set()
        new_origins_count = 0

        # iterate on each package's metadata
        for pkg_metadata in repo:
            if pkg_metadata.arch != "src":
                # not a source package, skip it
                continue

            # extract package metadata
            package_name = pkg_metadata.name

            # we extract the intrinsic version of the package for the rpm loader
            # to avoid creating different releases targeting the same directory
            # 2.12-10.el8 => 2.12-10
            package_version_split = pkg_metadata.vr.rsplit("-", maxsplit=1)
            package_version = "-".join(
                [
                    package_version_split[0],
                    package_version_split[1].split(".", maxsplit=1)[0],
                ]
            )

            # create package version key as expected by the rpm loader
            package_version_key = f"{release}/{component}/{package_version}"

            package_build_time = _get_last_modified(pkg_metadata)
            package_download_url = urljoin(
                repo.baseurl.rstrip("/") + "/", pkg_metadata.location
            )
            checksums = _get_checksums(pkg_metadata)

            # build origin url
            origin_url = self.origin_url_for_package(package_name)

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
                new_origins_count += 1

            # origins will be yielded when all pages processed
            origins_to_send.add(origin_url)

            # update package metadata in parameter that will be provided
            # to the rpm loader
            self.listed_origins[origin_url].extra_loader_arguments["packages"][
                package_version_key
            ] = {
                "name": package_name,
                "version": package_version,
                "url": package_download_url,
                "build_time": package_build_time.isoformat(),
                "checksums": checksums,
            }

            last_update = self.listed_origins[origin_url].last_update
            if last_update is not None and package_build_time > last_update:
                self.listed_origins[origin_url].last_update = package_build_time

            # add package version key to the set of found versions
            self.package_versions[package_name].add(package_version_key)

            # package has already been listed during a previous listing process
            if self.incremental and package_name in self.state.package_versions:
                new_versions = (
                    self.package_versions[package_name]
                    - self.state.package_versions[package_name]
                )
                # no new versions so far, no need to send the origin to the scheduler
                if not new_versions:
                    origins_to_send.remove(origin_url)

        logger.debug(
            "Found %s packages to update (%s new ones and %s packages with new versions).",
            len(origins_to_send),
            new_origins_count,
            len(origins_to_send) - new_origins_count,
        )
        logger.debug(
            "Current total number of listed source packages is equal to %s.",
            len(self.listed_origins),
        )

        self.origins_to_send.update(origins_to_send)

    def finalize(self):
        if self.incremental:
            # set mapping between listed package names and versions as lister state
            self.state.package_versions = self.package_versions
        self.updated = len(self.listed_origins) > 0
