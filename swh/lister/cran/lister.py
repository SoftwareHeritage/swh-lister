# Copyright (C) 2019-2020 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json
import logging
import subprocess
from typing import List, Mapping, Tuple

import pkg_resources

from swh.lister.core.simple_lister import SimpleLister
from swh.lister.cran.models import CRANModel
from swh.scheduler.utils import create_task_dict

logger = logging.getLogger(__name__)


CRAN_MIRROR = "https://cran.r-project.org"


class CRANLister(SimpleLister):
    MODEL = CRANModel
    LISTER_NAME = "cran"
    instance = "cran"

    def task_dict(
        self,
        origin_type,
        origin_url,
        version=None,
        html_url=None,
        policy=None,
        **kwargs,
    ):
        """Return task format dict. This creates tasks with args and kwargs
        set, for example::

            args: []
            kwargs: {
                'url': 'https://cran.r-project.org/Packages/<package>...',
                'artifacts': [{
                    'url': 'https://cran.r-project.org/...',
                    'version': '0.0.1',
                }]
            }

        """
        if not policy:
            policy = "oneshot"
        artifact_url = html_url
        assert origin_type == "tar"
        return create_task_dict(
            "load-cran",
            policy,
            url=origin_url,
            artifacts=[{"url": artifact_url, "version": version}],
            retries_left=3,
        )

    def safely_issue_request(self, identifier):
        """Bypass the implementation. It's now the `list_packages` which
        returns data.

        As an implementation detail, we cannot change simply the base
        SimpleLister yet as other implementation still uses it. This shall be
        part of another refactoring pass.

        """
        return None

    def list_packages(self, response) -> List[Mapping[str, str]]:
        """Runs R script which uses inbuilt API to return a json response
           containing data about the R packages.

        Returns:
            List of Dict about R packages. For example::

                [
                    {
                        'Package': 'A3',
                        'Version': '1.0.0',
                        'Title': 'A3 package',
                        'Description': ...
                    },
                    {
                        'Package': 'abbyyR',
                        'Version': '0.5.4',
                        'Title': 'Access to Abbyy OCR (OCR) API',
                        'Description': ...'
                    },
                    ...
                ]

        """
        return read_cran_data()

    def get_model_from_repo(self, repo: Mapping[str, str]) -> Mapping[str, str]:
        """Transform from repository representation to model

        """
        logger.debug("repo: %s", repo)
        origin_url, artifact_url = compute_origin_urls(repo)
        package = repo["Package"]
        version = repo["Version"]
        return {
            "uid": f"{package}-{version}",
            "name": package,
            "full_name": repo["Title"],
            "version": version,
            "html_url": artifact_url,
            "origin_url": origin_url,
            "origin_type": "tar",
        }


def read_cran_data() -> List[Mapping[str, str]]:
    """Execute r script to read cran listing.

    """
    filepath = pkg_resources.resource_filename("swh.lister.cran", "list_all_packages.R")
    logger.debug("script list-all-packages.R path: %s", filepath)
    response = subprocess.run(filepath, stdout=subprocess.PIPE, shell=False)
    return json.loads(response.stdout.decode("utf-8"))


def compute_origin_urls(repo: Mapping[str, str]) -> Tuple[str, str]:
    """Compute the package url from the repo dict.

    Args:
        repo: dict with key 'Package', 'Version'

    Returns:
        the tuple project url, artifact url

    """
    package = repo["Package"]
    version = repo["Version"]
    origin_url = f"{CRAN_MIRROR}/package={package}"
    artifact_url = f"{CRAN_MIRROR}/src/contrib/{package}_{version}.tar.gz"
    return origin_url, artifact_url
