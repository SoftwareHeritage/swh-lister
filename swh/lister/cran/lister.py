# Copyright (C) 2019 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json
import logging
import pkg_resources
import subprocess

from typing import List, Mapping

from swh.lister.cran.models import CRANModel

from swh.lister.core.simple_lister import SimpleLister
from swh.scheduler.utils import create_task_dict


logger = logging.getLogger(__name__)


def read_cran_data() -> List[Mapping[str, str]]:
    """Execute r script to read cran listing.

    """
    filepath = pkg_resources.resource_filename('swh.lister.cran',
                                               'list_all_packages.R')
    logger.debug('script list-all-packages.R path: %s', filepath)
    response = subprocess.run(filepath, stdout=subprocess.PIPE, shell=False)
    return json.loads(response.stdout.decode('utf-8'))


def compute_package_url(repo: Mapping[str, str]) -> str:
    """Compute the package url from the repo dict.

    Args:
        repo: dict with key 'Package', 'Version'

    Returns:
        the package url

    """
    return 'https://cran.r-project.org/src/contrib' \
        '/{Package}_{Version}.tar.gz'.format(**repo)


class CRANLister(SimpleLister):
    MODEL = CRANModel
    LISTER_NAME = 'cran'
    instance = 'cran'

    def task_dict(self, origin_type, origin_url, **kwargs):
        """Return task format dict. This creates tasks with args and kwargs
        set, for example::

            args: ['package', 'https://cran.r-project.org/...', 'version']
            kwargs: {}

        """
        policy = kwargs.get('policy', 'oneshot')
        package = kwargs.get('name')
        version = kwargs.get('version')
        return create_task_dict(
            'load-%s' % origin_type,
            policy, package, origin_url, version,
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
            List of Dict about r packages. For example:

            .. code-block:: python

                [
                    {
                        'Package': 'A3',
                        'Version': '1.0.0',
                        'Title':
                            'Accurate, Adaptable, and Accessible Error Metrics
                             for Predictive\nModels',
                        'Description':
                            'Supplies tools for tabulating and analyzing the
                             results of predictive models. The methods employed
                             are ... '
                    },
                    {
                        'Package': 'abbyyR',
                        'Version': '0.5.4',
                        'Title':
                            'Access to Abbyy OCR (OCR) API',
                        'Description': 'Get text from images of text using
                                        Abbyy Cloud Optical Character\n ...'
                    },
                    ...
                ]

        """
        return read_cran_data()

    def get_model_from_repo(
            self, repo: Mapping[str, str]) -> Mapping[str, str]:
        """Transform from repository representation to model

        """
        logger.debug('repo: %s', repo)
        project_url = compute_package_url(repo)
        package = repo['Package']
        return {
            'uid': package,
            'name': package,
            'full_name': repo['Title'],
            'version': repo['Version'],
            'html_url': project_url,
            'origin_url': project_url,
            'origin_type': 'tar',
        }
