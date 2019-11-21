# Copyright (C) 2018-2019 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
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
    instance = 'pypi'  # As of today only the main pypi.org is used

    def __init__(self, override_config=None):
        ListerOnePageApiTransport .__init__(self)
        SimpleLister.__init__(self, override_config=override_config)

    def task_dict(self, origin_type, origin_url, **kwargs):
        """(Override) Return task format dict

        This is overridden from the lister_base as more information is
        needed for the ingestion task creation.

        """
        _type = 'load-%s' % origin_type
        _policy = kwargs.get('policy', 'recurring')
        return utils.create_task_dict(
            _type, _policy, url=origin_url)

    def list_packages(self, response):
        """(Override) List the actual pypi origins from the response.

        """
        result = xmltodict.parse(response.content)
        _packages = [p['#text'] for p in result['html']['body']['a']]
        random.shuffle(_packages)
        return _packages

    def origin_url(self, repo_name: str) -> str:
        """Returns origin_url

        """
        return 'https://pypi.org/project/%s/' % repo_name

    def get_model_from_repo(self, repo_name):
        """(Override) Transform from repository representation to model

        """
        origin_url = self.origin_url(repo_name)
        return {
            'uid': origin_url,
            'name': repo_name,
            'full_name': repo_name,
            'html_url': origin_url,
            'origin_url': origin_url,
            'origin_type': 'pypi',
        }
