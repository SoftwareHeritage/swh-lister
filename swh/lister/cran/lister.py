# Copyright (C) 2019-2021 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from datetime import datetime, timezone
import json
import logging
import subprocess
from typing import Dict, Iterator, List, Optional, Tuple

import pkg_resources

from swh.lister.pattern import CredentialsType, StatelessLister
from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

logger = logging.getLogger(__name__)

CRAN_MIRROR = "https://cran.r-project.org"

PageType = List[Dict[str, str]]


class CRANLister(StatelessLister[PageType]):
    """
    List all packages hosted on The Comprehensive R Archive Network.
    """

    LISTER_NAME = "CRAN"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        credentials: Optional[CredentialsType] = None,
    ):
        super().__init__(
            scheduler, url=CRAN_MIRROR, instance="cran", credentials=credentials
        )

    def get_pages(self) -> Iterator[PageType]:
        """
        Yields a single page containing all CRAN packages info.
        """
        yield read_cran_data()

    def get_origins_from_page(self, page: PageType) -> Iterator[ListedOrigin]:
        assert self.lister_obj.id is not None
        for package_info in page:
            origin_url, artifact_url = compute_origin_urls(package_info)

            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                url=origin_url,
                visit_type="tar",
                last_update=parse_packaged_date(package_info),
                extra_loader_arguments={
                    "artifacts": [
                        {"url": artifact_url, "version": package_info["Version"]}
                    ]
                },
            )


def read_cran_data() -> List[Dict[str, str]]:
    """
    Runs R script which uses inbuilt API to return a json response
            containing data about the R packages.

    Returns:
        List of Dict about R packages. For example::

            [
                {
                    'Package': 'A3',
                    'Version': '1.0.0'
                },
                {
                    'Package': 'abbyyR',
                    'Version': '0.5.4'
                },
                ...
            ]
    """
    filepath = pkg_resources.resource_filename("swh.lister.cran", "list_all_packages.R")
    logger.debug("Executing R script %s", filepath)
    response = subprocess.run(filepath, stdout=subprocess.PIPE, shell=False)
    return json.loads(response.stdout.decode("utf-8"))


def compute_origin_urls(package_info: Dict[str, str]) -> Tuple[str, str]:
    """Compute the package url from the repo dict.

    Args:
        repo: dict with key 'Package', 'Version'

    Returns:
        the tuple project url, artifact url

    """
    package = package_info["Package"]
    version = package_info["Version"]
    origin_url = f"{CRAN_MIRROR}/package={package}"
    artifact_url = f"{CRAN_MIRROR}/src/contrib/{package}_{version}.tar.gz"
    return origin_url, artifact_url


def parse_packaged_date(package_info: Dict[str, str]) -> Optional[datetime]:
    packaged_at_str = package_info.get("Packaged", "")
    packaged_at = None
    if packaged_at_str:
        try:
            # Packaged field format: "%Y-%m-%d %H:%M:%S UTC; <packager>",
            packaged_at = datetime.strptime(
                packaged_at_str.split(" UTC;")[0], "%Y-%m-%d %H:%M:%S",
            ).replace(tzinfo=timezone.utc)
        except Exception:
            try:
                # Some old packages have a different date format:
                # "%a %b %d %H:%M:%S %Y; <packager>"
                packaged_at = datetime.strptime(
                    packaged_at_str.split(";")[0], "%a %b %d %H:%M:%S %Y",
                ).replace(tzinfo=timezone.utc)
            except Exception:
                logger.debug(
                    "Could not parse %s package release date: %s",
                    package_info["Package"],
                    packaged_at_str,
                )
    return packaged_at
