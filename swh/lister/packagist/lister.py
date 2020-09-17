# Copyright (C) 2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json
import logging
import random
from typing import Any, Dict, List, Mapping

from swh.lister.core.lister_transports import ListerOnePageApiTransport
from swh.lister.core.simple_lister import SimpleLister
from swh.scheduler import utils

from .models import PackagistModel

logger = logging.getLogger(__name__)


def compute_package_url(repo_name: str) -> str:
    """Compute packgist package url from repo name.

    """
    return "https://repo.packagist.org/p/%s.json" % repo_name


class PackagistLister(ListerOnePageApiTransport, SimpleLister):
    """List packages available in the Packagist package manager.

        The lister sends the request to the url present in the class
        variable `PAGE`, to receive a list of all the package names
        present in the Packagist package manager. Iterates over all the
        packages and constructs the metadata url of the package from
        the name of the package and creates a loading task::

            Task:
                Type: load-packagist
                Policy: recurring
                Args:
                    <package_name>
                    <package_metadata_url>

        Example::

            Task:
                Type: load-packagist
                Policy: recurring
                Args:
                    'hypejunction/hypegamemechanics'
                    'https://repo.packagist.org/p/hypejunction/hypegamemechanics.json'

    """

    MODEL = PackagistModel
    LISTER_NAME = "packagist"
    PAGE = "https://packagist.org/packages/list.json"
    instance = "packagist"

    def __init__(self, override_config=None):
        ListerOnePageApiTransport.__init__(self)
        SimpleLister.__init__(self, override_config=override_config)

    def task_dict(
        self, origin_type: str, origin_url: str, **kwargs: Mapping[str, str]
    ) -> Dict[str, Any]:
        """Return task format dict

        This is overridden from the lister_base as more information is
        needed for the ingestion task creation.

        """
        return utils.create_task_dict(
            "load-%s" % origin_type,
            kwargs.get("policy", "recurring"),
            kwargs.get("name"),
            origin_url,
            retries_left=3,
        )

    def list_packages(self, response: Any) -> List[str]:
        """List the actual packagist origins from the response.

        """
        response = json.loads(response.text)
        packages = [name for name in response["packageNames"]]
        logger.debug("Number of packages: %s", len(packages))
        random.shuffle(packages)
        return packages

    def get_model_from_repo(self, repo_name: str) -> Mapping[str, str]:
        """Transform from repository representation to model

        """
        url = compute_package_url(repo_name)
        return {
            "uid": repo_name,
            "name": repo_name,
            "full_name": repo_name,
            "html_url": url,
            "origin_url": url,
            "origin_type": "packagist",
        }
