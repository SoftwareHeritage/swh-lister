# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import random
import gzip
import json
import os
import requests
from urllib.parse import urlparse

from .models import GNUModel

from swh.scheduler import utils
from swh.lister.core.simple_lister import SimpleLister
from swh.model.hashutil import MultiHash, HASH_BLOCK_SIZE


class LocalResponse:
    """Local Response class with iter_content api

    """
    def __init__(self, path):
        self.path = path

    def iter_content(self, chunk_size=None):
        with open(self.path, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk


class ArchiveFetcher:
    """Http/Local client in charge of downloading archives from a
       remote/local server.

    Args:
        temp_directory (str): Path to the temporary disk location used
                              for downloading the release artifacts

    """
    def __init__(self, temp_directory=None):
        self.temp_directory = os.getcwd()
        self.session = requests.session()
        self.params = {
            'headers': {
                'User-Agent': 'Software Heritage Lister ( __devl__)'
            }
        }

    def download(self, url):
        """Download the remote tarball url locally.

        Args:
            url (str): Url (file or http*)

        Raises:
            ValueError in case of failing to query

        Returns:
            Tuple of local (filepath, hashes of filepath)

        """
        url_parsed = urlparse(url)
        if url_parsed.scheme == 'file':
            path = url_parsed.path
            response = LocalResponse(path)
            length = os.path.getsize(path)
        else:
            response = self.session.get(url, **self.params, stream=True)
            if response.status_code != 200:
                raise ValueError("Fail to query '%s'. Reason: %s" % (
                    url, response.status_code))
            length = int(response.headers['content-length'])

        filepath = os.path.join(self.temp_directory, os.path.basename(url))

        h = MultiHash(length=length)
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=HASH_BLOCK_SIZE):
                h.update(chunk)
                f.write(chunk)

        actual_length = os.path.getsize(filepath)
        if length != actual_length:
            raise ValueError('Error when checking size: %s != %s' % (
                length, actual_length))

        return filepath


class GNULister(SimpleLister, ArchiveFetcher):
    MODEL = GNUModel
    LISTER_NAME = 'gnu'
    TREE_URL = 'https://ftp.gnu.org/tree.json.gz'

    def __init__(self, override_config=None):
        SimpleLister.__init__(self, override_config=override_config)
        ArchiveFetcher.__init__(self, override_config=override_config)

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

    def download_file(self):
        '''
            Downloads tree.json file and returns its location

            Returns
            File path of the downloaded file
        '''
        file_path, hash_dict = self.download(self.TREE_URL)
        return file_path

    def read_downloaded_file(self, file_path):
        '''
            Reads the downloaded file content and convert it into json format

            Returns
            File content in json format
        '''
        with gzip.GzipFile(file_path, 'r') as fin:
            response = json.loads(fin.read().decode('utf-8'))
        return response

    def safely_issue_request(self, identifier):
        '''(Override)Make network request with to download the file which
            has file structure of the GNU website.

            Args:
                identifier: resource identifier
            Returns:
                server response
        '''
        file_path = self.download_file()
        response = self.read_downloaded_file(file_path)
        return response

    def list_packages(self, response):
        """(Override) List the actual gnu origins with their names and
            time last updated from the response.

        """
        response = clean_up_response(response)
        _packages = []
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
                    _packages.append(repo_details)
        random.shuffle(_packages)
        return _packages

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
