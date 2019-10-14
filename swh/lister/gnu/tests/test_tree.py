# Copyright (C) 2019 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json

import pytest

from os import path
from swh.lister.gnu.tree import (
    GNUTree, find_artifacts, check_filename_is_archive, load_raw_data
)


def test_load_raw_data_from_query(requests_mock_datadir):
    actual_json = load_raw_data('https://ftp.gnu.org/tree.json.gz')
    assert actual_json is not None
    assert isinstance(actual_json, list)
    assert len(actual_json) == 2


def test_load_raw_data_from_query_failure(requests_mock_datadir):
    inexistant_url = 'https://ftp2.gnu.org/tree.unknown.gz'
    with pytest.raises(ValueError, match='Error during query'):
        load_raw_data(inexistant_url)


def test_load_raw_data_from_file(datadir):
    filepath = path.join(datadir, 'https_ftp.gnu.org', 'tree.json.gz')
    actual_json = load_raw_data(filepath)
    assert actual_json is not None
    assert isinstance(actual_json, list)
    assert len(actual_json) == 2


def test_load_raw_data_from_file_failure(datadir):
    unknown_path = path.join(datadir, 'ftp.gnu.org2', 'tree.json.gz')
    with pytest.raises(FileNotFoundError):
        load_raw_data(unknown_path)


def test_tree_json(requests_mock_datadir):
    tree_json = GNUTree('https://ftp.gnu.org/tree.json.gz')

    assert tree_json.projects['https://ftp.gnu.org/gnu/8sync/'] == {
        'name': '8sync',
        'time_modified': '1489817408',
        'url': 'https://ftp.gnu.org/gnu/8sync/'
    }

    assert tree_json.projects['https://ftp.gnu.org/gnu/3dldf/'] == {
        'name': '3dldf',
        'time_modified': '1386961236',
        'url': 'https://ftp.gnu.org/gnu/3dldf/'
    }

    assert tree_json.projects['https://ftp.gnu.org/gnu/a2ps/'] == {
        'name': 'a2ps',
        'time_modified': '1198900505',
        'url': 'https://ftp.gnu.org/gnu/a2ps/'
    }

    assert tree_json.projects['https://ftp.gnu.org/old-gnu/xshogi/'] == {
        'name': 'xshogi',
        'time_modified': '1059822922',
        'url': 'https://ftp.gnu.org/old-gnu/xshogi/'
    }

    assert tree_json.artifacts['https://ftp.gnu.org/old-gnu/zlibc/'] == [
        {
            'archive': 'https://ftp.gnu.org/old-gnu/zlibc/zlibc-0.9b.tar.gz',  # noqa
            'length': 90106,
            'time': 857980800
        },
        {
            'archive': 'https://ftp.gnu.org/old-gnu/zlibc/zlibc-0.9e.tar.gz',  # noqa
            'length': 89625,
            'time': 860396400
        }
    ]


def test_tree_json_failures(requests_mock_datadir):
    url = 'https://unknown/tree.json.gz'
    tree_json = GNUTree(url)

    with pytest.raises(ValueError, match='Error during query to %s' % url):
        tree_json.artifacts['https://ftp.gnu.org/gnu/3dldf/']

    with pytest.raises(ValueError, match='Error during query to %s' % url):
        tree_json.projects['https://ftp.gnu.org/old-gnu/xshogi/']


def test_find_artifacts_small_sample(datadir):
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

    file_structure = json.load(open(path.join(datadir, 'tree.min.json')))
    actual_tarballs = find_artifacts(file_structure, '/root/')
    assert actual_tarballs == expected_tarballs


def test_find_artifacts(datadir):
    file_structure = json.load(open(path.join(datadir, 'tree.json')))
    actual_tarballs = find_artifacts(file_structure, '/root/')
    assert len(actual_tarballs) == 42 + 3  # tar + zip


def test_check_filename_is_archive():
    for ext in ['abc.xy.zip', 'cvb.zip', 'abc.tar.bz2', 'something.tar']:
        assert check_filename_is_archive(ext) is True

    for ext in ['abc.tar.gz.sig', 'abc', 'something.zip2', 'foo.tar.']:
        assert check_filename_is_archive(ext) is False
