# Copyright (C) 2022-2024  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import datetime
import logging
from pathlib import Path
import re
import tarfile
import tempfile
from typing import Any, Dict, Iterator, List, Optional
from urllib.parse import unquote, urljoin

from bs4 import BeautifulSoup

from swh.model.hashutil import hash_to_hex
from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, StatelessLister

logger = logging.getLogger(__name__)

# Aliasing the page results returned by `get_pages` method from the lister.
ArchListerPage = List[Dict[str, Any]]


class ArchLister(StatelessLister[ArchListerPage]):
    """List Arch linux origins from 'core', 'extra', and 'community' repositories

    For 'official' Arch Linux it downloads core.tar.gz, extra.tar.gz and community.tar.gz
    from https://archive.archlinux.org/repos/last/ extract to a temp directory and
    then walks through each 'desc' files.

    Each 'desc' file describe the latest released version of a package and helps
    to build an origin url from where scrapping artifacts metadata.

    For 'arm' Arch Linux it follow the same discovery process parsing 'desc' files.
    The main difference is that we can't get existing versions of an arm package
    because https://archlinuxarm.org does not have an 'archive' website or api.
    """

    LISTER_NAME = "arch"
    VISIT_TYPE = "arch"
    INSTANCE = "arch"

    BASE_URL = "https://archlinux.org"
    ARCH_PACKAGE_URL_PATTERN = "{base_url}/packages/{repo}/{arch}/{pkgname}"
    ARCH_PACKAGE_VERSIONS_URL_PATTERN = "{base_url}/packages/{pkgname[0]}/{pkgname}"
    ARCH_PACKAGE_DOWNLOAD_URL_PATTERN = (
        "{base_url}/packages/{pkgname[0]}/{pkgname}/{filename}"
    )
    ARCH_API_URL_PATTERN = "{base_url}/packages/{repo}/{arch}/{pkgname}/json"

    ARM_PACKAGE_URL_PATTERN = "{base_url}/packages/{arch}/{pkgname}"
    ARM_PACKAGE_DOWNLOAD_URL_PATTERN = "{base_url}/{arch}/{repo}/{filename}"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: str = BASE_URL,
        instance: str = INSTANCE,
        credentials: Optional[CredentialsType] = None,
        max_origins_per_page: Optional[int] = None,
        max_pages: Optional[int] = None,
        enable_origins: bool = True,
        flavours: Dict[str, Any] = {
            "official": {
                "archs": ["x86_64"],
                "repos": ["core", "extra", "community"],
                "base_info_url": "https://archlinux.org",
                "base_archive_url": "https://archive.archlinux.org",
                "base_mirror_url": "",
                "base_api_url": "https://archlinux.org",
            },
            "arm": {
                "archs": ["armv7h", "aarch64"],
                "repos": ["core", "extra", "community"],
                "base_info_url": "https://archlinuxarm.org",
                "base_archive_url": "",
                "base_mirror_url": "https://uk.mirror.archlinuxarm.org",
                "base_api_url": "",
            },
        },
    ):
        super().__init__(
            scheduler=scheduler,
            credentials=credentials,
            url=url,
            instance=instance,
            max_origins_per_page=max_origins_per_page,
            max_pages=max_pages,
            enable_origins=enable_origins,
        )

        self.flavours = flavours

    def scrap_package_versions(
        self, name: str, repo: str, base_url: str
    ) -> List[Dict[str, Any]]:
        """Given a package 'name' and 'repo', make an http call to origin url and parse
        its content to get package versions artifacts data.  That method is suitable
        only for 'official' Arch Linux, not 'arm'.

        Args:
            name: Package name
            repo: The repository the package belongs to (one of self.repos)

        Returns:
            A list of dict of version

            Example::

                [
                    {"url": "https://archive.archlinux.org/packages/d/dialog/dialog-1:1.3_20190211-1-x86_64.pkg.tar.xz",  # noqa: B950
                    "arch": "x86_64",
                    "repo": "core",
                    "name": "dialog",
                    "version": "1:1.3_20190211-1",
                    "filename": "dialog-1:1.3_20190211-1-x86_64.pkg.tar.xz",
                    "last_modified": "2019-02-13T08:36:00"},
                ]

        """
        url = self.ARCH_PACKAGE_VERSIONS_URL_PATTERN.format(
            pkgname=name, base_url=base_url
        )
        response = self.http_request(url)
        soup = BeautifulSoup(response.text, "html.parser")
        links = soup.select("a[href]")

        # drop the first line (used to go to up directory)
        if links and links[0].attrs["href"] == "../":
            links.pop(0)

        versions = []

        for link in links:
            # filename displayed can be cropped if name is too long, get it from href instead
            filename = unquote(link.attrs["href"])

            if filename.endswith((".tar.xz", ".tar.zst")):
                # Extract arch from filename
                arch_rex = re.compile(
                    rf"^{re.escape(name)}-(?P<version>.*)-(?P<arch>any|i686|x86_64)"
                    rf"(.pkg.tar.(?:zst|xz))$"
                )
                m = arch_rex.match(filename)
                if m is None:
                    logger.error(
                        "Can not find a match for architecture in %(filename)s",
                        dict(filename=filename),
                    )
                else:
                    arch = m.group("arch")
                    version = m.group("version")

                # Extract last_modified date
                last_modified = None
                raw_text = link.next_sibling
                if raw_text:
                    raw_text_rex = re.compile(
                        r"^(?P<last_modified>\d+-\w+-\d+ \d\d:\d\d)\s+.*$"
                    )
                    s = raw_text_rex.search(raw_text.text.strip())
                    if s is None:
                        logger.error(
                            "Can not find a match for 'last_modified' in '%(raw_text)s'",
                            dict(raw_text=raw_text),
                        )
                    else:
                        values = s.groups()
                        assert values and len(values) == 1
                        last_modified_str = values[0]

                    # format as expected
                    last_modified = datetime.datetime.strptime(
                        last_modified_str, "%d-%b-%Y %H:%M"
                    ).isoformat()

                # link url is relative, format a canonical one
                url = self.ARCH_PACKAGE_DOWNLOAD_URL_PATTERN.format(
                    base_url=base_url, pkgname=name, filename=filename
                )
                versions.append(
                    dict(
                        name=name,
                        version=version,
                        repo=repo,
                        arch=arch,
                        filename=filename,
                        url=url,
                        last_modified=last_modified,
                    )
                )
        return versions

    def get_repo_archive(self, url: str, destination_path: Path) -> Path:
        """Given an url and a destination path, retrieve and extract .tar.gz archive
        which contains 'desc' file for each package.
        Each .tar.gz archive corresponds to an Arch Linux repo ('core', 'extra', 'community').

        Args:
            url: url of the .tar.gz archive to download
            destination_path: the path on disk where to extract archive

        Returns:
            a directory Path where the archive has been extracted to.
        """
        res = self.http_request(url)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        destination_path.write_bytes(res.content)

        extract_to = Path(str(destination_path).split(".tar.gz")[0])
        tar = tarfile.open(destination_path)
        tar.extractall(path=extract_to)
        tar.close()

        return extract_to

    def parse_desc_file(
        self,
        path: Path,
        repo: str,
        base_url: str,
        dl_url_fmt: str,
    ) -> Dict[str, Any]:
        """Extract package information from a 'desc' file.
        There are subtle differences between parsing 'official' and 'arm' des files

        Args:
            path: A path to a 'desc' file on disk
            repo: The repo the package belongs to

        Returns:
            A dict of metadata

            Example::

                {'api_url': 'https://archlinux.org/packages/core/x86_64/dialog/json',
                 'arch': 'x86_64',
                 'base': 'dialog',
                 'builddate': '1650081535',
                 'csize': '203028',
                 'desc': 'A tool to display dialog boxes from shell scripts',
                 'filename': 'dialog-1:1.3_20220414-1-x86_64.pkg.tar.zst',
                 'isize': '483988',
                 'license': 'LGPL2.1',
                 'md5sum': '06407c0cb11c50d7bf83d600f2e8107c',
                 'name': 'dialog',
                 'packager': 'Evangelos Foutras <foutrelis@archlinux.org>',
                 'pgpsig': 'pgpsig content xxx',
                 'project_url': 'https://invisible-island.net/dialog/',
                 'provides': 'libdialog.so=15-64',
                 'repo': 'core',
                 'sha256sum': 'ef8c8971f591de7db0f455970ef5d81d5aced1ddf139f963f16f6730b1851fa7',
                 'url': 'https://archive.archlinux.org/packages/.all/dialog-1:1.3_20220414-1-x86_64.pkg.tar.zst',  # noqa: B950
                 'version': '1:1.3_20220414-1'}
        """
        rex = re.compile(r"^\%(?P<k>\w+)\%\n(?P<v>.*)\n$", re.M)
        with path.open("rb") as content:
            parsed = rex.findall(content.read().decode())
            data = {entry[0].lower(): entry[1] for entry in parsed}

            if "url" in data.keys():
                data["project_url"] = data["url"]

            assert data["name"]
            assert data["filename"]
            assert data["arch"]

            data["repo"] = repo
            data["url"] = urljoin(
                base_url,
                dl_url_fmt.format(
                    base_url=base_url,
                    pkgname=data["name"],
                    filename=data["filename"],
                    arch=data["arch"],
                    repo=repo,
                ),
            )

            assert data["md5sum"]
            assert data["sha256sum"]
            data["checksums"] = {
                "md5sum": hash_to_hex(data["md5sum"]),
                "sha256sum": hash_to_hex(data["sha256sum"]),
            }
        return data

    def get_pages(self) -> Iterator[ArchListerPage]:
        """Yield an iterator sorted by name in ascending order of pages.

        Each page is a list of package belonging to a flavour ('official', 'arm'),
        and a repo ('core', 'extra', 'community')
        """

        for name, flavour in self.flavours.items():
            for arch in flavour["archs"]:
                for repo in flavour["repos"]:
                    yield self._get_repo_page(name, flavour, arch, repo)

    def _get_repo_page(
        self, name: str, flavour: Dict[str, Any], arch: str, repo: str
    ) -> ArchListerPage:
        with tempfile.TemporaryDirectory() as tmpdir:
            page = []
            if name == "official":
                prefix = urljoin(flavour["base_archive_url"], "/repos/last/")
                filename = f"{repo}.files.tar.gz"
                archive_url = urljoin(prefix, f"{repo}/os/{arch}/{filename}")
                destination_path = Path(tmpdir, arch, filename)
                base_url = flavour["base_archive_url"]
                dl_url_fmt = self.ARCH_PACKAGE_DOWNLOAD_URL_PATTERN
                base_info_url = flavour["base_info_url"]
                info_url_fmt = self.ARCH_PACKAGE_URL_PATTERN
            elif name == "arm":
                filename = f"{repo}.files.tar.gz"
                archive_url = urljoin(
                    flavour["base_mirror_url"], f"{arch}/{repo}/{filename}"
                )
                destination_path = Path(tmpdir, arch, filename)
                base_url = flavour["base_mirror_url"]
                dl_url_fmt = self.ARM_PACKAGE_DOWNLOAD_URL_PATTERN
                base_info_url = flavour["base_info_url"]
                info_url_fmt = self.ARM_PACKAGE_URL_PATTERN

            archive = self.get_repo_archive(
                url=archive_url, destination_path=destination_path
            )

            assert archive

            packages_desc = list(archive.glob("**/desc"))
            logger.debug(
                "Processing %(instance)s source packages info from "
                "%(flavour)s %(arch)s %(repo)s repository, "
                "(%(qty)s packages).",
                dict(
                    instance=self.instance,
                    flavour=name,
                    arch=arch,
                    repo=repo,
                    qty=len(packages_desc),
                ),
            )

            for package_desc in packages_desc:
                data = self.parse_desc_file(
                    path=package_desc,
                    repo=repo,
                    base_url=base_url,
                    dl_url_fmt=dl_url_fmt,
                )

                assert data["builddate"]
                last_modified = datetime.datetime.fromtimestamp(
                    float(data["builddate"]), tz=datetime.timezone.utc
                )

                assert data["name"]
                assert data["filename"]
                assert data["arch"]
                url = info_url_fmt.format(
                    base_url=base_info_url,
                    pkgname=data["name"],
                    filename=data["filename"],
                    repo=repo,
                    arch=data["arch"],
                )

                assert data["version"]
                if name == "official":
                    # find all versions of a package scrapping archive
                    versions = self.scrap_package_versions(
                        name=data["name"], repo=repo, base_url=base_url
                    )
                elif name == "arm":
                    # There is no way to get related versions of a package,
                    # but 'data' represents the latest released version,
                    # use it in this case
                    assert data["builddate"]
                    assert data["csize"]
                    assert data["url"]
                    versions = [
                        dict(
                            name=data["name"],
                            version=data["version"],
                            repo=repo,
                            arch=data["arch"],
                            filename=data["filename"],
                            url=data["url"],
                            last_modified=last_modified.replace(tzinfo=None).isoformat(
                                timespec="seconds"
                            ),
                        )
                    ]

                package = {
                    "name": data["name"],
                    "version": data["version"],
                    "last_modified": last_modified,
                    "url": url,
                    "versions": versions,
                    "data": data,
                }
                page.append(package)
            return page

    def get_origins_from_page(self, page: ArchListerPage) -> Iterator[ListedOrigin]:
        """Iterate on all arch pages and yield ListedOrigin instances."""
        assert self.lister_obj.id is not None
        for origin in page:
            artifacts = []
            arch_metadata = []
            for version in origin["versions"]:
                artifacts.append(
                    {
                        "version": version["version"],
                        "filename": version["filename"],
                        "url": version["url"],
                    }
                )
                if version["version"] == origin["version"]:
                    artifacts[-1]["checksums"] = {
                        "md5": origin["data"]["md5sum"],
                        "sha256": origin["data"]["sha256sum"],
                    }
                else:
                    artifacts[-1]["checksums"] = {}

                arch_metadata.append(
                    {
                        "version": version["version"],
                        "name": version["name"],
                        "arch": version["arch"],
                        "repo": version["repo"],
                        "last_modified": version["last_modified"],
                    }
                )
            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                visit_type=self.VISIT_TYPE,
                url=origin["url"],
                last_update=origin["last_modified"],
                extra_loader_arguments={
                    "artifacts": artifacts,
                    "arch_metadata": arch_metadata,
                },
            )
