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
    BASE_URL = 'https://ftp.gnu.org'
    instance = 'gnu'

    def task_dict(self, origin_type, origin_url, **kwargs):
        """
        Return task format dict

        This is overridden from the lister_base as more information is
        needed for the ingestion task creation.
        """
        return utils.create_task_dict(
            'load-%s' % origin_type, 'recurring', kwargs.get('name'),
            origin_url, list_of_tarballs=kwargs.get('list_of_tarballs'))

    def get_file(self):
        '''
        Downloads and unzip tree.json.gz file and returns its content
        in JSON format

        Returns
        File content in JSON format
        '''
        response = requests.get(self.TREE_URL,
                                allow_redirects=True)
        uncompressed_content = gzip.decompress(response.content)
        return json.loads(uncompressed_content.decode('utf-8'))

    def safely_issue_request(self, identifier):
        '''
        Make network request with to download the file which
        has file structure of the GNU website.

        Args:
            identifier: resource identifier
        Returns:
            server response
        '''
        return self.get_file()

    def list_packages(self, response):
        """
        List the actual gnu origins with their names and
        time last updated from the response.

        Args:
            response : File structure of the website
            in JSON format

        Returns:
            a list of all the packages with their names, url of their root
            directory and the tarballs present for the particular package.
            [
                {'name': '3dldf', 'url': 'https://ftp.gnu.org/gnu/3dldf/',
                 'list_of_tarballs':
                    [
                        {'archive':
                            'https://ftp.gnu.org/gnu/3dldf/3DLDF-1.1.3.tar.gz',
                        'date': '1071002600'},
                        {'archive':
                            'https://ftp.gnu.org/gnu/3dldf/3DLDF-1.1.4.tar.gz',
                        'date': '1071078759'}}
                    ]
                },
                {'name': '8sync', 'url': 'https://ftp.gnu.org/gnu/8sync/',
                'list_of_tarballs':
                    [
                        {'archive':
                            'https://ftp.gnu.org/gnu/8sync/8sync-0.1.0.tar.gz',
                        'date': '1461357336'},
                        {'archive':
                            'https://ftp.gnu.org/gnu/8sync/8sync-0.2.0.tar.gz',
                        'date': '1480991830'}
                    ]
            ]
        """
        response = filter_directories(response)
        packages = []
        for directory in response:
            content = directory['contents']
            for repo in content:
                if repo['type'] == 'directory':
                    package_url = '%s/%s/%s/' % (self.BASE_URL,
                                                 directory['name'],
                                                 repo['name'])
                    list_of_tarballs = find_tarballs(
                                      repo['contents'], package_url)
                    if list_of_tarballs != []:
                        repo_details = {
                            'name': repo['name'],
                            'url': package_url,
                            'list_of_tarballs ': list_of_tarballs
                        }
                        packages.append(repo_details)
        random.shuffle(packages)
        return packages

    def get_model_from_repo(self, repo):
        """Transform from repository representation to model

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
        """Transform response to list for model manipulation

        """
        return [self.get_model_from_repo(repo) for repo in response]

    def transport_request(self):
        pass

    def transport_response_to_string(self):
        pass

    def transport_quota_check(self):
        pass


def find_tarballs(package_file_structure, url):
    '''
    Recursively lists all the tarball present in the folder and
    subfolders for a particular package url.

    Args
        package_file_structure : File structure of the package root directory
        url : URL of the corresponding package

    Returns
        List of all the tarball urls and the last their time of update
        example-
        For a package called 3dldf

        [
            {'archive': 'https://ftp.gnu.org/gnu/3dldf/3DLDF-1.1.3.tar.gz',
                                                        'date': '1071002600'}
            {'archive': 'https://ftp.gnu.org/gnu/3dldf/3DLDF-1.1.4.tar.gz',
                                                        'date': '1071078759'}
            {'archive': 'https://ftp.gnu.org/gnu/3dldf/3DLDF-1.1.5.1.tar.gz',
                                                        'date': '1074278633'}
            ...
        ]
    '''
    list_of_tarballs = []
    for single_file in package_file_structure:
        file_type = single_file['type']
        file_name = single_file['name']
        if file_type == 'file':
            if(file_name[-6:-3] == "tar" or
               file_name[-3:] == "zip"):
                list_of_tarballs .append({
                    "archive": url + file_name,
                    "date": single_file['time']
                })
        # It will recursively check for tarballs in all sub-folders
        elif file_type == 'directory':
            list_of_tarballs_in_dir = find_tarballs(
                                      single_file['contents'],
                                      url + file_name + '/')
            list_of_tarballs .extend(list_of_tarballs_in_dir)

    return list_of_tarballs


def filter_directories(response):
    '''
    Removes unnecessary directories from JSON response and
    keep only gnu/ and old-gnu/
    '''
    final_response = []
    file_system = response[0]['contents']
    for directory in file_system:
        if directory['name'] in ('gnu', 'old-gnu'):
            final_response.append(directory)
    return final_response
