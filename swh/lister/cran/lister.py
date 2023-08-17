# Copyright (C) 2019-2023 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from collections import defaultdict
import logging
import os
import tempfile
from typing import Any, Dict, Iterator, List, Optional, Tuple
from urllib.parse import urljoin

import iso8601
import pyreadr

from swh.lister.pattern import CredentialsType, StatelessLister
from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

logger = logging.getLogger(__name__)

CRAN_MIRROR_URL = "https://cran.r-project.org"
CRAN_INFO_DB_URL = f"{CRAN_MIRROR_URL}/web/dbs/cran_info_db.rds"

# List[Tuple[origin_url, List[Dict[package_version, package_metdata]]]]
PageType = List[Tuple[str, List[Dict[str, Any]]]]


class CRANLister(StatelessLister[PageType]):
    """
    List all packages hosted on The Comprehensive R Archive Network.

    The lister parses and reads the content of the weekly CRAN database
    dump in RDS format referencing all downloadable package tarballs.
    """

    LISTER_NAME = "cran"
    INSTANCE = "cran"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: str = CRAN_MIRROR_URL,
        instance: str = INSTANCE,
        credentials: Optional[CredentialsType] = None,
        max_origins_per_page: Optional[int] = None,
        max_pages: Optional[int] = None,
        enable_origins: bool = True,
    ):
        super().__init__(
            scheduler,
            url=url,
            instance=instance,
            credentials=credentials,
            max_origins_per_page=max_origins_per_page,
            max_pages=max_pages,
            enable_origins=enable_origins,
        )

    def get_pages(self) -> Iterator[PageType]:
        """
        Yields a single page containing all CRAN packages info.
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            package_artifacts: Dict[str, Dict[str, Any]] = defaultdict(dict)
            dest_path = os.path.join(tmpdir, os.path.basename(CRAN_INFO_DB_URL))
            logger.debug("Fetching %s file to %s", CRAN_INFO_DB_URL, dest_path)
            dest_path = pyreadr.download_file(CRAN_INFO_DB_URL, dest_path)
            logger.debug("Parsing %s file", dest_path)
            cran_db_df = pyreadr.read_r(dest_path)[None]

            logger.debug("Processing CRAN packages")
            for package_artifact_metadata in cran_db_df.itertuples():
                tarball_path = package_artifact_metadata[0]
                package_info = tarball_path.split("/")[-1].replace(".tar.gz", "")
                if "_" not in package_info and "-" not in package_info:
                    # skip package artifact with no version
                    continue

                try:
                    package_name, package_version = package_info.split("_", maxsplit=1)
                except ValueError:
                    # old artifacts can separate name and version with a dash
                    package_name, package_version = package_info.split("-", maxsplit=1)

                package_artifacts[package_name][package_version] = {
                    "url": urljoin(
                        CRAN_MIRROR_URL, tarball_path.replace("/srv/ftp/pub/R", "")
                    ),
                    "version": package_version,
                    "package": package_name,
                    "checksums": {"length": int(package_artifact_metadata.size)},
                    "mtime": iso8601.parse_date(
                        package_artifact_metadata.mtime.isoformat()
                    ),
                }

            yield [
                (f"{CRAN_MIRROR_URL}/package={package_name}", list(artifacts.values()))
                for package_name, artifacts in package_artifacts.items()
            ]

    def get_origins_from_page(self, page: PageType) -> Iterator[ListedOrigin]:
        assert self.lister_obj.id is not None

        for origin_url, artifacts in page:
            mtimes = [artifact.pop("mtime") for artifact in artifacts]

            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                url=origin_url,
                visit_type="cran",
                last_update=max(mtimes),
                extra_loader_arguments={
                    "artifacts": list(sorted(artifacts, key=lambda a: a["version"]))
                },
            )
