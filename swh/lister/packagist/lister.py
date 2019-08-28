# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import random
import json
from .models import PackagistModel

from swh.scheduler import utils
from swh.lister.core.simple_lister import SimpleLister
from swh.lister.core.lister_transports import ListerOnePageApiTransport


class PackagistLister(ListerOnePageApiTransport, SimpleLister):
    """List packages available in the Packagist package manger.

        The lister sends the request to the url present in the class
        variable `PAGE`, to receive a list of all the package names
        present in the Packagist package manger. Iterates over all the
        packages and constructs the metadata url of the package from
        the name of the package and creates a loading task.

        Task:
            Type: load-packagist
            Policy: recurring
            Args:
                <package_name>
                <package_metadata_url>

        Example:
            Type: load-packagist
            Policy: recurring
            Args:
                'hypejunction/hypegamemechanics'
                'https://repo.packagist.org/p/hypejunction/hypegamemechanics.json'

    """
    MODEL = PackagistModel
    LISTER_NAME = 'packagist'
    PAGE = 'https://packagist.org/packages/list.json'
    instance = 'packagist'

    def __init__(self, override_config=None):
        ListerOnePageApiTransport .__init__(self)
        SimpleLister.__init__(self, override_config=override_config)

    def task_dict(self, origin_type, origin_url, **kwargs):
        """Return task format dict

        This is overridden from the lister_base as more information is
        needed for the ingestion task creation.

        """
        return utils.create_task_dict('load-%s' % origin_type,
                                      kwargs.get('policy', 'recurring'),
                                      kwargs.get('name'), origin_url)

    def list_packages(self, response):
        """List the actual packagist origins from the response.

        """
        response = json.loads(response.text)
        packages = [name for name in response['packageNames']]
        random.shuffle(packages)
        return packages

    def get_model_from_repo(self, repo_name):
        """Transform from repository representation to model

        """
        url = 'https://repo.packagist.org/p/%s.json' % repo_name
        return {
            'uid': repo_name,
            'name': repo_name,
            'full_name': repo_name,
            'html_url': url,
            'origin_url': url,
            'origin_type': 'packagist',
        }

    def transport_response_simplified(self, response):
        """Transform response to list for model manipulation

        """
        return [self.get_model_from_repo(repo_name) for repo_name in response]
