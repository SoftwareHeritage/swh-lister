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


def test_find_tarballs_small_sample():
    expected_tarballs = [
        {
            'archive': '/root/artanis/artanis-0.2.1.tar.bz2',
            'time': 1495205979,
            'length': 424081,
        },
        {
            'archive': '/root/xboard/winboard/winboard-4_0_0-src.zip',  # noqa
            'time': 898422900,
            'length': 1514448
        },
        {
            'archive': '/root/xboard/xboard-3.6.2.tar.gz',  # noqa
            'time': 869814000,
            'length': 450164,
        },
        {
            'archive': '/root/xboard/xboard-4.0.0.tar.gz',  # noqa
            'time': 898422900,
            'length': 514951,
        },
    ]

    file_structure = json.load(open('swh/lister/gnu/tests/tree.min.json'))
    actual_tarballs = find_tarballs(file_structure, '/root/')
    assert actual_tarballs == expected_tarballs


def test_find_tarballs():
    file_structure = json.load(open('swh/lister/gnu/tests/tree.json'))
    actual_tarballs = find_tarballs(file_structure, '/root/')
    assert len(actual_tarballs) == 42 + 3  # tar + zip


def test_file_extension_check():
    assert file_extension_check('abc.xy.zip')
    assert file_extension_check('cvb.zip')
    assert file_extension_check('abc.tar.bz2')
    assert file_extension_check('abc') is False
