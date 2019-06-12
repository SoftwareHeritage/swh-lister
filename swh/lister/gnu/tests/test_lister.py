# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json

from swh.lister.gnu.lister import find_tarballs, filter_directories
from swh.lister.gnu.lister import file_extension_check


def test_filter_directories():
    f = open('swh/lister/gnu/tests/api_response.json')
    api_response = json.load(f)
    cleared_api_response = filter_directories(api_response)
    for directory in cleared_api_response:
        if directory['name'] not in ('gnu', 'old-gnu'):
            assert False


def test_find_tarballs():
    f = open('swh/lister/gnu/tests/find_tarballs_output.json')
    expected_list_of_all_tarballs = json.load(f)

    f = open('swh/lister/gnu/tests/file_structure.json')
    file_structure = json.load(f)
    list_of_all_tarballs = []
    list_of_all_tarballs.extend(
        find_tarballs(file_structure[0]['contents'],
                      "https://ftp.gnu.org/gnu/artanis/"))
    list_of_all_tarballs.extend(
        find_tarballs(file_structure[1]['contents'],
                      "https://ftp.gnu.org/old-gnu/xboard/"))
    assert list_of_all_tarballs == expected_list_of_all_tarballs


def test_file_extension_check():
    assert file_extension_check('abc.xy.zip')
    assert file_extension_check('cvb.zip')
    assert file_extension_check('abc.tar.bz2')
    assert file_extension_check('abc') is False
