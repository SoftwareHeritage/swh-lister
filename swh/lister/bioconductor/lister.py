# Copyright (C) 2023-2024  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from dataclasses import dataclass, field
import json
import logging
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from debian.deb822 import Sources
import iso8601
from packaging import version
from requests import HTTPError

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, Lister

logger = logging.getLogger(__name__)

Release = str
Category = str
BioconductorListerPage = Optional[Tuple[Release, Category, Dict[str, Any]]]


@dataclass
class BioconductorListerState:
    """State of the Bioconductor lister"""

    package_versions: Dict[str, Set[str]] = field(default_factory=dict)
    """Dictionary mapping a package name to all the versions found during
    last listing"""


class BioconductorLister(Lister[BioconductorListerState, BioconductorListerPage]):
    """List origins from Bioconductor, a collection of open source software
    for bioinformatics based on the R statistical programming language."""

    LISTER_NAME = "bioconductor"
    VISIT_TYPE = "bioconductor"
    INSTANCE = "bioconductor"

    BIOCONDUCTOR_HOMEPAGE = "https://www.bioconductor.org"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: str = BIOCONDUCTOR_HOMEPAGE,
        instance: str = INSTANCE,
        credentials: Optional[CredentialsType] = None,
        releases: Optional[List[Release]] = None,
        categories: Optional[List[Category]] = None,
        incremental: bool = False,
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
            max_origins_per_page=max_origins_per_page,
            max_pages=max_pages,
            enable_origins=enable_origins,
            record_batch_size=record_batch_size,
        )

        if releases is None:
            self.releases = self.fetch_versions()
        else:
            self.releases = releases

        self.categories = categories or [
            "bioc",
            "workflows",
            "data/annotation",
            "data/experiment",
        ]

        self.incremental = incremental

        self.listed_origins: Dict[str, ListedOrigin] = {}
        self.origins_to_send: Set[str] = set()
        self.package_versions: Dict[str, Set[str]] = {}

    def state_from_dict(self, d: Dict[str, Any]) -> BioconductorListerState:
        return BioconductorListerState(
            package_versions={k: set(v) for k, v in d.items()}
        )

    def state_to_dict(self, state: BioconductorListerState) -> Dict[str, Any]:
        return {k: list(v) for k, v in state.package_versions.items()}

    def origin_url_for_package(self, package_name: str) -> str:
        return f"{self.BIOCONDUCTOR_HOMEPAGE}/packages/{package_name}"

    def get_pages(self) -> Iterator[BioconductorListerPage]:
        """Return an iterator for each page. Every page is a (release, category) pair."""
        for release in self.releases:
            if version.parse(release) < version.parse("1.8"):
                # only bioc category existed before 1.8
                url_template = urljoin(
                    self.url, "/packages/{category}/{release}/src/contrib/PACKAGES"
                )
                categories = {"bioc"}
            elif version.parse(release) < version.parse("2.5"):
                # workflows category won't exist for these
                url_template = urljoin(
                    self.url, "/packages/{release}/{category}/src/contrib/PACKAGES"
                )
                categories = {"bioc", "data/annotation", "data/experiment"}
            else:
                url_template = urljoin(
                    self.url, "/packages/json/{release}/{category}/packages.json"
                )
                categories = set(self.categories)

            for category in categories:
                url = url_template.format(release=release, category=category)
                try:
                    packages_txt = self.http_request(url).text
                    packages = self.parse_packages(packages_txt)
                except HTTPError as e:
                    assert e.response is not None
                    logger.debug(
                        "Skipping page since got %s response for %s",
                        e.response.status_code,
                        url,
                    )
                    continue

                yield (release, category, packages)

        # Yield extra none to signal get_origins_from_page()
        # to stop iterating and yield the extracted origins
        yield None

    def fetch_versions(self) -> List[str]:
        html = self.http_request(
            f"{self.BIOCONDUCTOR_HOMEPAGE}/about/release-announcements"
        ).text
        bs = BeautifulSoup(html, "html.parser")

        return [
            tr.select("td")[0].text
            for tr in reversed(bs.select("table tbody tr"))
            if tr.select("td")[2].select("a")
        ]

    def parse_packages(self, text: str) -> Dict[str, Any]:
        """Parses packages.json and PACKAGES files"""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        sources = Sources.iter_paragraphs(text)
        return {s["Package"]: dict(s) for s in sources}

    def get_origins_from_page(
        self, page: BioconductorListerPage
    ) -> Iterator[ListedOrigin]:
        """Convert a page of BioconductorLister PACKAGES/packages.json
        metadata into a list of ListedOrigins"""
        assert self.lister_obj.id is not None

        if page is None:
            for origin_url in self.origins_to_send:
                yield self.listed_origins[origin_url]

            return

        release, category, packages = page

        origins_to_send = set()

        for pkg_name, pkg_metadata in packages.items():
            pkg_version = pkg_metadata["Version"]
            last_update_date = None
            last_update_str = ""

            if version.parse(release) < version.parse("1.8"):
                tar_url = urljoin(
                    self.url,
                    f"/packages/{category}/{release}/src/contrib/Source/{pkg_name}_{pkg_metadata['Version']}.tar.gz",
                )
            elif version.parse(release) < version.parse("2.5"):
                tar_url = urljoin(
                    self.url,
                    f"/packages/{release}/{category}/src/contrib/{pkg_name}_{pkg_metadata['Version']}.tar.gz",
                )
            else:
                # Some packages don't have don't have a download URL (based on source.ver)
                # and hence can't be archived. For example see the package
                # maEndToEnd at the end of
                # https://bioconductor.org/packages/json/3.17/workflows/packages.json

                # Even guessing tar url path based on the expected url format doesn't work. i.e.
                # https://bioconductor.org/packages/3.17/workflows/src/contrib/maEndToEnd_2.20.0.tar.gz
                # doesn't respond with a tar file. Plus, the mirror clearly shows
                # that maEndToEnd tar is missing.
                # https://ftp.gwdg.de/pub/misc/bioconductor/packages/3.17/workflows/src/contrib/
                # So skipping such packages

                if "source.ver" not in pkg_metadata:
                    logger.info(
                        (
                            "Skipping package %s listed in release %s "
                            "category %s since it doesn't have a download URL"
                        ),
                        pkg_name,
                        release,
                        category,
                    )
                    continue

                if "git_url" in pkg_metadata:
                    # Along with the .tar.gz files grab the git repo as well
                    git_origin_url = pkg_metadata["git_url"]
                    git_last_update_str = pkg_metadata.get("git_last_commit_date")
                    self.listed_origins[git_origin_url] = ListedOrigin(
                        lister_id=self.lister_obj.id,
                        visit_type="git",
                        url=git_origin_url,
                        last_update=(
                            iso8601.parse_date(git_last_update_str)
                            if git_last_update_str
                            else None
                        ),
                    )
                    origins_to_send.add(git_origin_url)

                tar_url = urljoin(
                    self.url,
                    f"/packages/{release}/{category}/{pkg_metadata['source.ver']}",
                )

                last_update_str = pkg_metadata.get(
                    "Date/Publication", pkg_metadata.get("git_last_commit_date")
                )
                last_update_date = (
                    iso8601.parse_date(last_update_str) if last_update_str else None
                )
                # For some packages in releases >= 2.5, last_update can still
                # remain None. Example: See "adme16cod.db" entry in
                # https://bioconductor.org/packages/json/3.17/data/annotation/packages.json

            origin_url = self.origin_url_for_package(pkg_name)
            package_version_key = f"{release}/{category}/{pkg_version}"

            if origin_url not in self.listed_origins:
                self.listed_origins[origin_url] = ListedOrigin(
                    lister_id=self.lister_obj.id,
                    visit_type=self.VISIT_TYPE,
                    url=origin_url,
                    last_update=last_update_date,
                    extra_loader_arguments={"packages": {}},
                )

                self.package_versions[pkg_name] = set()

            origins_to_send.add(origin_url)

            optional_fields: Dict[str, Any] = {}
            if "MD5sum" in pkg_metadata:
                optional_fields["checksums"] = {"md5": pkg_metadata["MD5sum"]}
            if last_update_str:
                optional_fields["last_update_date"] = last_update_str

            self.listed_origins[origin_url].extra_loader_arguments["packages"][
                package_version_key
            ] = {
                "release": release,
                "version": pkg_version,
                "category": category,
                "package": pkg_name,
                "tar_url": tar_url,
            }

            self.listed_origins[origin_url].extra_loader_arguments["packages"][
                package_version_key
            ].update(optional_fields)

            last_update = self.listed_origins[origin_url].last_update
            if (
                last_update is not None
                and last_update_date is not None
                and last_update_date > last_update
            ):
                self.listed_origins[origin_url].last_update = last_update_date

            self.package_versions[pkg_name].add(package_version_key)

            # package has been listed during a previous listing
            if self.incremental and pkg_name in self.state.package_versions:
                new_versions = (
                    self.package_versions[pkg_name]
                    - self.state.package_versions[pkg_name]
                )
                # no new versions, no need to send the origin to the scheduler
                if not new_versions:
                    origins_to_send.remove(origin_url)

        self.origins_to_send.update(origins_to_send)

    def finalize(self) -> None:
        if self.incremental:
            self.state.package_versions = self.package_versions

        self.updated = len(self.listed_origins) > 0
