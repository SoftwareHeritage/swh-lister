# Copyright (C) 2019 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging


logger = logging.getLogger(__name__)


def test_lister_no_page_check_results(swh_listers, requests_mock_datadir):
    lister = swh_listers['gnu']

    lister.run()

    r = lister.scheduler.search_tasks(task_type='load-tar')
    assert len(r) == 383

    for row in r:
        assert row['type'] == 'load-tar'
        # arguments check
        args = row['arguments']['args']
        assert len(args) == 1

        url = args[0]
        assert url.startswith('https://ftp.gnu.org')

        url_suffix = url.split('https://ftp.gnu.org')[1]
        assert 'gnu' in url_suffix or 'old-gnu' in url_suffix

        # kwargs
        kwargs = row['arguments']['kwargs']
        assert list(kwargs.keys()) == ['tarballs']

        tarballs = kwargs['tarballs']
        # check the tarball's structure
        tarball = tarballs[0]
        assert set(tarball.keys()) == set(['archive', 'length', 'time'])

        assert row['policy'] == 'oneshot'
