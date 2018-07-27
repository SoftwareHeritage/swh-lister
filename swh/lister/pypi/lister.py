# Copyright (C) 2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from .models import PyPiModel

from swh.scheduler import utils
from swh.lister.core.simple_lister import SimpleLister
from swh.lister.core.lister_transports import ListerXMLRPCTransport


class PyPiLister(ListerXMLRPCTransport, SimpleLister):
    # Template path expecting an integer that represents the page id
    MODEL = PyPiModel
    LISTER_NAME = 'pypi'
    SERVER = 'https://pypi.org/pypi'

    def __init__(self, override_config=None):
        ListerXMLRPCTransport.__init__(self)
        SimpleLister.__init__(self, override_config=override_config)

    def task_dict(self, origin_type, origin_url, **kwargs):
        """(Override) Return task format dict

        This is overridden from the lister_base as more information is
        needed for the ingestion task creation.

        """
        _type = 'origin-update-%s' % origin_type
        _policy = 'recurring'
        project_metadata_url = kwargs.get('html_url')
        return utils.create_task_dict(
            _type, _policy, origin_url,
            project_metadata_url=project_metadata_url)

    def list_packages(self, client):
        """(Override) List the actual pypi origins from the api.

        """
        return client.list_packages()

    def _compute_urls(self, repo_name):
        """Returns a tuple (project_url, project_metadata_url)

        """
        return (
            'https://pypi.org/pypi/%s/' % repo_name,
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
