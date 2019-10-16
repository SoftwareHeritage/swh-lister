# Copyright (C) 2019 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging


logger = logging.getLogger(__name__)


def test_gnu_lister(swh_listers, requests_mock_datadir):
    lister = swh_listers['gnu']

    lister.run()

    r = lister.scheduler.search_tasks(task_type='load-tar')
    assert len(r) == 383

    for row in r:
        assert row['type'] == 'load-tar'
        # arguments check
        args = row['arguments']['args']
        assert len(args) == 0

        # kwargs
        kwargs = row['arguments']['kwargs']
        assert set(kwargs.keys()) == {'url', 'artifacts'}

        url = kwargs['url']
        assert url.startswith('https://ftp.gnu.org')

        url_suffix = url.split('https://ftp.gnu.org')[1]
        assert 'gnu' in url_suffix or 'old-gnu' in url_suffix

        artifacts = kwargs['artifacts']
        # check the artifact's structure
        artifact = artifacts[0]
        assert set(artifact.keys()) == {
            'url', 'length', 'time', 'filename', 'version'
        }

        assert row['policy'] == 'oneshot'
