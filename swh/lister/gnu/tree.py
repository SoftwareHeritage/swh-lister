# Copyright (C) 2019 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import gzip
import json
import logging
import requests

from pathlib import Path
from typing import Dict, Tuple, List
from urllib.parse import urlparse


logger = logging.getLogger(__name__)


def load_raw_data(url: str) -> List[Dict]:
    """Load the raw json from the tree.json.gz

    Args:
        url: Tree.json.gz url or path

    Returns:
        The raw json list

    """
    if url.startswith('http://') or url.startswith('https://'):
        response = requests.get(url, allow_redirects=True)
        if not response.ok:
            raise ValueError('Error during query to %s' % url)
        raw = gzip.decompress(response.content)
    else:
        with gzip.open(url, 'r') as f:
            raw = f.read()
    raw_data = json.loads(raw.decode('utf-8'))
    return raw_data


class GNUTree:
    """Gnu Tree's representation

    """
    def __init__(self, url: str):
        self.url = url  # filepath or uri
        u = urlparse(url)
        self.base_url = '%s://%s' % (u.scheme, u.netloc)
        # Interesting top level directories
        self.top_level_directories = ['gnu', 'old-gnu']
        # internal state
        self._artifacts = {}  # type: Dict
        self._projects = {}  # type: Dict

    @property
    def projects(self) -> Dict:
        if not self._projects:
            self._projects, self._artifacts = self._load()
        return self._projects

    @property
    def artifacts(self) -> Dict:
        if not self._artifacts:
            self._projects, self._artifacts = self._load()
        return self._artifacts

    def _load(self) -> Tuple[Dict, Dict]:
        """Compute projects and artifacts per project

        Returns:
            Tuple of dict projects (key project url, value the associated
            information) and a dict artifacts (key project url, value the
            info_file list)

        """
        projects = {}
        artifacts = {}

        raw_data = load_raw_data(self.url)[0]
        for directory in raw_data['contents']:
            if directory['name'] not in self.top_level_directories:
                continue
            infos = directory['contents']
            for info in infos:
                if info['type'] == 'directory':
                    package_url = '%s/%s/%s/' % (
                        self.base_url, directory['name'], info['name'])
                    package_artifacts = find_artifacts(
                        info['contents'], package_url)
                    if package_artifacts != []:
                        repo_details = {
                            'name': info['name'],
                            'url': package_url,
                            'time_modified': info['time'],
                        }
                        artifacts[package_url] = package_artifacts
                        projects[package_url] = repo_details

        return projects, artifacts


def find_artifacts(filesystem: List[Dict], url: str) -> List[Dict]:
    """Recursively list artifacts present in the folder and subfolders for a
    particular package url.

    Args:

        filesystem: File structure of the package root directory. This is a
            list of Dict representing either file or directory information as
            dict (keys: name, size, time, type).
        url: URL of the corresponding package

    Returns
        List of tarball urls and their associated metadata (time, length).
        For example:

        .. code-block:: python

            [
                {'archive': 'https://ftp.gnu.org/gnu/3dldf/3DLDF-1.1.3.tar.gz',
                 'time': 1071002600,
                 'length': 543},
                {'archive': 'https://ftp.gnu.org/gnu/3dldf/3DLDF-1.1.4.tar.gz',
                 'time': 1071078759,
                 'length': 456},
                {'archive': 'https://ftp.gnu.org/gnu/3dldf/3DLDF-1.1.5.tar.gz',
                 'time': 1074278633,
                 'length': 251},
                ...
            ]

    """
    artifacts = []
    for info_file in filesystem:
        filetype = info_file['type']
        filename = info_file['name']
        if filetype == 'file':
            if check_filename_is_archive(filename):
                artifacts.append({
                    'archive': url + filename,
                    'time': int(info_file['time']),
                    'length': int(info_file['size']),
                })
        # It will recursively check for artifacts in all sub-folders
        elif filetype == 'directory':
            tarballs_in_dir = find_artifacts(
                info_file['contents'],
                url + filename + '/')
            artifacts.extend(tarballs_in_dir)

    return artifacts


def check_filename_is_archive(filename: str) -> bool:
    """
    Check for the extension of the file, if the file is of zip format of
    .tar.x format, where x could be anything, then returns true.

    Args:
        filename: name of the file for which the extensions is needs to
            be checked.

    Returns:
        Whether filename is an archive or not

    Example:

    >>> check_filename_is_archive('abc.zip')
    True
    >>> check_filename_is_archive('abc.tar.gz')
    True
    >>> check_filename_is_archive('bac.tar')
    True
    >>> check_filename_is_archive('abc.tar.gz.sig')
    False
    >>> check_filename_is_archive('foobar.tar.')
    False

    """
    file_suffixes = Path(filename).suffixes
    logger.debug('Path(%s).suffixed: %s' % (filename, file_suffixes))
    if len(file_suffixes) == 1 and file_suffixes[-1] in ('.zip', '.tar'):
        return True
    elif len(file_suffixes) > 1:
        if file_suffixes[-1] == '.zip' or file_suffixes[-2] == '.tar':
            return True
    return False
