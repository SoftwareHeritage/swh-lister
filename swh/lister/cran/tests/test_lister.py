# Copyright (C) 2019-2020 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json
import pytest

from os import path
from unittest.mock import patch

from swh.lister.cran.lister import compute_package_url


def test_cran_compute_package_url():
    url = compute_package_url({'Package': 'something', 'Version': '0.0.1'})

    assert url == 'https://cran.r-project.org/src/contrib/%s_%s.tar.gz' % (
        'something',
        '0.0.1',
    )


def test_cran_compute_package_url_failure():
    for incomplete_repo in [{'Version': '0.0.1'}, {'Package': 'package'}, {}]:
        with pytest.raises(KeyError):
            compute_package_url(incomplete_repo)


@patch('swh.lister.cran.lister.read_cran_data')
def test_cran_lister_cran(mock_cran, datadir, lister_cran):
    lister = lister_cran

    with open(path.join(datadir, 'list-r-packages.json')) as f:
        data = json.loads(f.read())

    mock_cran.return_value = data
    assert len(data) == 6

    lister.run()

    r = lister.scheduler.search_tasks(task_type='load-cran')
    assert len(r) == 6

    for row in r:
        assert row['type'] == 'load-cran'
        # arguments check
        args = row['arguments']['args']
        assert len(args) == 0

        # kwargs
        kwargs = row['arguments']['kwargs']
        assert len(kwargs) == 2
        assert set(kwargs.keys()) == {'url', 'version'}

        assert row['policy'] == 'oneshot'
        assert row['retries_left'] == 3
