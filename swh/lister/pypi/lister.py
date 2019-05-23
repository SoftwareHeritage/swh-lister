# Copyright (C) 2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import random
import xmltodict

from .models import PyPIModel

from swh.scheduler import utils
from swh.lister.core.simple_lister import SimpleLister
from swh.lister.core.lister_transports import ListerOnePageApiTransport


class PyPILister(ListerOnePageApiTransport, SimpleLister):
    MODEL = PyPIModel
    LISTER_NAME = 'pypi'
    PAGE = 'https://pypi.org/simple/'

    def __init__(self, override_config=None):
        ListerOnePageApiTransport .__init__(self)
        SimpleLister.__init__(self, override_config=override_config)

    def task_dict(self, origin_type, origin_url, **kwargs):
        """(Override) Return task format dict

        This is overridden from the lister_base as more information is
        needed for the ingestion task creation.

        """
        _type = 'load-%s' % origin_type
        _policy = 'recurring'
        project_name = kwargs.get('name')
        project_metadata_url = kwargs.get('html_url')
        return utils.create_task_dict(
            _type, _policy, project_name, origin_url,
            project_metadata_url=project_metadata_url)

    def list_packages(self, response):
        """(Override) List the actual pypi origins from the response.

        """
        result = xmltodict.parse(response.content)
        _packages = [p['#text'] for p in result['html']['body']['a']]
        random.shuffle(_packages)
        return _packages

    def _compute_urls(self, repo_name):
        """Returns a tuple (project_url, project_metadata_url)

        """
        return (
            'https://pypi.org/project/%s/' % repo_name,
            'https://pypi.org/pypi/%s/json' % repo_name
        )

    def get_model_from_repo(self, repo_name):
        """(Override) Transform from repository representation to model

        """
        project_url, project_url_meta = self._compute_urls(repo_name)
        return {
            'uid': repo_name,
            'name': repo_name,
            'full_name': repo_name,
            'html_url': project_url_meta,
            'origin_url': project_url,
            'origin_type': 'pypi',
            'description': None,
        }

    def transport_response_simplified(self, response):
        """(Override) Transform response to list for model manipulation

        """
        return [self.get_model_from_repo(repo_name) for repo_name in response]
