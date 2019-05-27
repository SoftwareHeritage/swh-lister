# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import random
import gzip
import json
import requests

from .models import GNUModel

from swh.scheduler import utils
from swh.lister.core.simple_lister import SimpleLister


class GNULister(SimpleLister):
    MODEL = GNUModel
    LISTER_NAME = 'gnu'
    TREE_URL = 'https://ftp.gnu.org/tree.json.gz'

    def __init__(self, override_config=None):
        SimpleLister.__init__(self, override_config=override_config)

    def task_dict(self, origin_type, origin_url, **kwargs):
        """(Override)
        Return task format dict

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

    def get_file(self):
        '''
            Downloads and unzip tree.json.gz file and returns its content
            in JSON format

            Returns
            File content in JSON format
        '''
        response = requests.get('https://ftp.gnu.org/tree.json.gz',
                                allow_redirects=True)
        uncompressed_content = gzip.decompress(response.content)
        return json.loads(uncompressed_content.decode('utf-8'))

    def safely_issue_request(self, identifier):
        '''(Override)Make network request with to download the file which
            has file structure of the GNU website.

            Args:
                identifier: resource identifier
            Returns:
                server response
        '''
        response = self.get_file()
        return response

    def list_packages(self, response):
        """(Override) List the actual gnu origins with their names and
            time last updated from the response.
        """
        response = clean_up_response(response)
        packages = []
        for directory in response:
            content = directory['contents']
            for repo in content:
                if repo['type'] == 'directory':
                    repo_details = {
                        'name': repo['name'],
                        'url': self._get_project_url(directory['name'],
                                                     repo['name']),
                        'time_modified': repo['time']
                    }
                    packages.append(repo_details)
        random.shuffle(packages)
        return packages

    def _get_project_url(self, dir_name, package_name):
        """Returns project_url

        """
        return 'https://ftp.gnu.org/%s/%s/' % (dir_name, package_name)

    def get_model_from_repo(self, repo):
        """(Override) Transform from repository representation to model

        """
        return {
            'uid': repo['name'],
            'name': repo['name'],
            'full_name': repo['name'],
            'html_url': repo['url'],
            'origin_url': repo['url'],
            'time_last_upated': repo['time_modified'],
            'origin_type': 'gnu',
            'description': None,
        }

    def transport_response_simplified(self, response):
        """(Override) Transform response to list for model manipulation

        """
        return [self.get_model_from_repo(repo) for repo in response]

    def transport_request(self):
        pass

    def transport_response_to_string(self):
        pass

    def transport_quota_check(self):
        pass


def clean_up_response(response):
    final_response = []
    file_system = response[0]['content']
    for directory in file_system:
        if directory['name'] in ('gnu', 'mirrors', 'old-gnu'):
            final_response.append(directory)
    return final_response
