# Copyright (C) 2019-2021 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from datetime import datetime, timezone
import gzip
import json
import logging
from os import path
from pathlib import Path
import re
from typing import Any, List, Mapping, Sequence, Tuple
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)


class GNUTree:
    """Gnu Tree's representation

    """

    def __init__(self, url: str):
        self.url = url  # filepath or uri
        u = urlparse(url)
        self.base_url = "%s://%s" % (u.scheme, u.netloc)
        # Interesting top level directories
        self.top_level_directories = ["gnu", "old-gnu"]
        # internal state
        self._artifacts = {}  # type: Mapping[str, Any]
        self._projects = {}  # type: Mapping[str, Any]

    @property
    def projects(self) -> Mapping[str, Any]:
        if not self._projects:
            self._projects, self._artifacts = self._load()
        return self._projects

    @property
    def artifacts(self) -> Mapping[str, Any]:
        if not self._artifacts:
            self._projects, self._artifacts = self._load()
        return self._artifacts

    def _load(self) -> Tuple[Mapping[str, Any], Mapping[str, Any]]:
        """Compute projects and artifacts per project

        Returns:
            Tuple of dict projects (key project url, value the associated
            information) and a dict artifacts (key project url, value the
            info_file list)

        """
        projects = {}
        artifacts = {}

        raw_data = load_raw_data(self.url)[0]
        for directory in raw_data["contents"]:
            if directory["name"] not in self.top_level_directories:
                continue
            infos = directory["contents"]
            for info in infos:
                if info["type"] == "directory":
                    package_url = "%s/%s/%s/" % (
                        self.base_url,
                        directory["name"],
                        info["name"],
                    )
                    package_artifacts = find_artifacts(info["contents"], package_url)
                    if package_artifacts != []:
                        repo_details = {
                            "name": info["name"],
                            "url": package_url,
                            "time_modified": format_date(info["time"]),
                        }
                        artifacts[package_url] = package_artifacts
                        projects[package_url] = repo_details

        return projects, artifacts


def find_artifacts(
    filesystem: List[Mapping[str, Any]], url: str
) -> List[Mapping[str, Any]]:
    """Recursively list artifacts present in the folder and subfolders for a
    particular package url.

    Args:

        filesystem: File structure of the package root directory. This is a
            list of Dict representing either file or directory information as
            dict (keys: name, size, time, type).
        url: URL of the corresponding package

    Returns
        List of tarball urls and their associated metadata (time, length,
        etc...). For example:

        .. code-block:: python

            [
                {
                    'url': 'https://ftp.gnu.org/gnu/3dldf/3DLDF-1.1.3.tar.gz',
                    'time': 1071002600,
                    'filename': '3DLDF-1.1.3.tar.gz',
                    'version': '1.1.3',
                    'length': 543
                },
                {
                    'url': 'https://ftp.gnu.org/gnu/3dldf/3DLDF-1.1.4.tar.gz',
                    'time': 1071078759,
                    'filename: '3DLDF-1.1.4.tar.gz',
                    'version': '1.1.4',
                    'length': 456
                },
                {
                    'url': 'https://ftp.gnu.org/gnu/3dldf/3DLDF-1.1.5.tar.gz',
                    'time': 1074278633,
                    'filename': '3DLDF-1.1.5.tar.gz',
                    'version': '1.1.5'
                    'length': 251
                },
                ...
            ]

    """
    artifacts = []  # type: List[Mapping[str, Any]]
    for info_file in filesystem:
        filetype = info_file["type"]
        filename = info_file["name"]
        if filetype == "file":
            if check_filename_is_archive(filename):
                uri = url + filename
                artifacts.append(
                    {
                        "url": uri,
                        "filename": filename,
                        "time": format_date(info_file["time"]),
                        "length": int(info_file["size"]),
                        "version": get_version(filename),
                    }
                )
        # It will recursively check for artifacts in all sub-folders
        elif filetype == "directory":
            tarballs_in_dir = find_artifacts(
                info_file["contents"], url + filename + "/"
            )
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
    if len(file_suffixes) == 1 and file_suffixes[-1] in (".zip", ".tar"):
        return True
    elif len(file_suffixes) > 1:
        if file_suffixes[-1] == ".zip" or file_suffixes[-2] == ".tar":
            return True
    return False


# to recognize existing naming pattern
EXTENSIONS = [
    "zip",
    "tar",
    "gz",
    "tgz",
    "bz2",
    "bzip2",
    "lzma",
    "lz",
    "xz",
    "Z",
    "7z",
]

VERSION_KEYWORDS = [
    "cygwin_me",
    "w32",
    "win32",
    "nt",
    "cygwin",
    "mingw",
    "latest",
    "alpha",
    "beta",
    "release",
    "stable",
    "hppa",
    "solaris",
    "sunos",
    "sun4u",
    "sparc",
    "sun",
    "aix",
    "ibm",
    "rs6000",
    "i386",
    "i686",
    "linux",
    "redhat",
    "linuxlibc",
    "mips",
    "powerpc",
    "macos",
    "apple",
    "darwin",
    "macosx",
    "powermacintosh",
    "unknown",
    "netbsd",
    "freebsd",
    "sgi",
    "irix",
]

# Match a filename into components.
#
# We use Debian's release number heuristic: A release number starts
# with a digit, and is followed by alphanumeric characters or any of
# ., +, :, ~ and -
#
# We hardcode a list of possible extensions, as this release number
# scheme would match them too... We match on any combination of those.
#
# Greedy matching is done right to left (we only match the extension
# greedily with +, software_name and release_number are matched lazily
# with +? and *?).

PATTERN = r"""
^
(?:
    # We have a software name and a release number, separated with a
    # -, _ or dot.
    (?P<software_name1>.+?[-_.])
    (?P<release_number>({vkeywords}|[0-9][0-9a-zA-Z_.+:~-]*?)+)
|
    # We couldn't match a release number, put everything in the
    # software name.
    (?P<software_name2>.+?)
)
(?P<extension>(?:\.(?:{extensions}))+)
$
""".format(
    extensions="|".join(EXTENSIONS),
    vkeywords="|".join("%s[-]?" % k for k in VERSION_KEYWORDS),
)


def get_version(uri: str) -> str:
    """Extract branch name from tarball uri

    Args:
        uri (str): Tarball URI

    Returns:
        Version detected

    Example:
        >>> uri = 'https://ftp.gnu.org/gnu/8sync/8sync-0.2.0.tar.gz'
        >>> get_version(uri)
        '0.2.0'

        >>> uri = '8sync-0.3.0.tar.gz'
        >>> get_version(uri)
        '0.3.0'

    """
    filename = path.split(uri)[-1]
    m = re.match(PATTERN, filename, flags=re.VERBOSE | re.IGNORECASE)
    if m:
        d = m.groupdict()
        if d["software_name1"] and d["release_number"]:
            return d["release_number"]
        if d["software_name2"]:
            return d["software_name2"]

    return ""


def load_raw_data(url: str) -> Sequence[Mapping]:
    """Load the raw json from the tree.json.gz

    Args:
        url: Tree.json.gz url or path

    Returns:
        The raw json list

    """
    if url.startswith("http://") or url.startswith("https://"):
        response = requests.get(url, allow_redirects=True)
        if not response.ok:
            raise ValueError("Error during query to %s" % url)
        raw = gzip.decompress(response.content)
    else:
        with gzip.open(url, "r") as f:
            raw = f.read()
    raw_data = json.loads(raw.decode("utf-8"))
    return raw_data


def format_date(timestamp: str) -> str:
    """Format a string timestamp to an isoformat string

    """
    return datetime.fromtimestamp(int(timestamp), tz=timezone.utc).isoformat()
