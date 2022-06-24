# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information
import datetime
import gzip
import json
import logging
from pathlib import Path
import shutil
from typing import Any, Dict, Iterator, Optional

import requests

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, StatelessLister

logger = logging.getLogger(__name__)

# Aliasing the page results returned by `get_pages` method from the lister.
AurListerPage = Dict[str, Any]


class AurLister(StatelessLister[AurListerPage]):
    """List Arch User Repository (AUR) origins.

    Given an url (used as a base url, default is 'https://aur.archlinux.org'),
    download a 'packages-meta-v1.json.gz' which contains a json file listing all
    existing packages definitions.

    Each entry describes the latest released version of a package. The origin url
    for a package is built using 'pkgname' and corresponds to a git repository.

    An rpc api exists but it is recommended to save bandwidth so it's not used. See
    https://lists.archlinux.org/pipermail/aur-general/2021-November/036659.html
    for more on this.
    """

    LISTER_NAME = "aur"
    VISIT_TYPE = "aur"
    INSTANCE = "aur"

    BASE_URL = "https://aur.archlinux.org"
    DEFAULT_PACKAGES_INDEX_URL = "{base_url}/packages-meta-v1.json.gz"
    PACKAGE_VCS_URL_PATTERN = "{base_url}/{pkgname}.git"
    PACKAGE_SNAPSHOT_URL_PATTERN = "{base_url}/cgit/aur.git/snapshot/{pkgname}.tar.gz"

    DESTINATION_PATH = Path("/tmp/aur_archive")

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

    def download_index_archive(self) -> Path:
        """Build an url based on self.DEFAULT_PACKAGES_INDEX_URL format string,
        and download the archive to self.DESTINATION_PATH

        Returns:
            a directory Path where the archive has been downloaded to.
        """
        url = self.DEFAULT_PACKAGES_INDEX_URL.format(base_url=self.url)
        filename = url.split("/")[-1]
        destination = Path(self.DESTINATION_PATH, filename)

        if not Path(self.DESTINATION_PATH).exists():
            Path(self.DESTINATION_PATH).mkdir()

        response = requests.get(url, stream=True)
        destination.write_bytes(response.raw.read())
        assert destination.exists()

        return destination

    def get_pages(self) -> Iterator[AurListerPage]:
        """Yield an iterator which returns 'page'

        Each page corresponds to a package with a 'version', an 'url' for a Git
        repository, a 'project_url' which represents the upstream project url and
        a canonical 'snapshot_url' from which a tar.gz archive of the package can
        be downloaded.
        """
        index = self.download_index_archive()

        with gzip.open(index, "rb") as f:
            assert f.readable()
            file_content = f.read()
            packages = json.loads(file_content)

        assert packages

        counter: int = 0
        for package in packages:
            # Exclude lines where Name differs from PackageBase as they represents
            # split package and they don't have resolvable snapshots url
            if package["Name"] == package["PackageBase"]:
                pkgname = package["PackageBase"]
                version = package["Version"]
                project_url = package["URL"]
                last_modified = datetime.datetime.fromtimestamp(
                    float(package["LastModified"]), tz=datetime.timezone.utc
                ).isoformat()
                counter += 1
                yield {
                    "pkgname": pkgname,
                    "version": version,
                    "url": self.PACKAGE_VCS_URL_PATTERN.format(
                        base_url=self.BASE_URL, pkgname=pkgname
                    ),
                    "snapshot_url": self.PACKAGE_SNAPSHOT_URL_PATTERN.format(
                        base_url=self.BASE_URL, pkgname=pkgname
                    ),
                    "project_url": project_url,
                    "last_modified": last_modified,
                }
        logger.debug("Found %s AUR packages in aur_index", counter)

    def get_origins_from_page(self, origin: AurListerPage) -> Iterator[ListedOrigin]:
        """Iterate on all pages and yield ListedOrigin instances.
        It uses the vcs (Git) url as an origin and adds `artifacts` and `aur_metadata`
        entries to 'extra_loader_arguments'.

        `artifacts` describe the file to download and `aur_metadata` store some
        metadata that can be useful for the loader.
        """
        assert self.lister_obj.id is not None

        url = origin["url"]
        last_update = datetime.datetime.fromisoformat(origin["last_modified"])
        filename = origin["snapshot_url"].split("/")[-1]

        artifacts = [
            {
                "filename": filename,
                "url": origin["snapshot_url"],
                "version": origin["version"],
            }
        ]
        aur_metadata = [
            {
                "version": origin["version"],
                "project_url": origin["project_url"],
                "last_update": origin["last_modified"],
                "pkgname": origin["pkgname"],
            }
        ]

        yield ListedOrigin(
            lister_id=self.lister_obj.id,
            visit_type=self.VISIT_TYPE,
            url=url,
            last_update=last_update,
            extra_loader_arguments={
                "artifacts": artifacts,
                "aur_metadata": aur_metadata,
            },
        )

    def finalize(self) -> None:
        # Cleanup by removing the repository directory
        if self.DESTINATION_PATH.exists():
            shutil.rmtree(self.DESTINATION_PATH)
            logger.debug(
                "Successfully removed %s directory", str(self.DESTINATION_PATH)
            )
