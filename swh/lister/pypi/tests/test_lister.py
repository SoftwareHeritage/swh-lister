# Copyright (C) 2019 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


def test_pypi_lister(swh_listers, requests_mock_datadir):
    lister = swh_listers['pypi']

    lister.run()

    r = lister.scheduler.search_tasks(task_type='load-pypi')
    assert len(r) == 4

    for row in r:
        assert row['type'] == 'load-pypi'
        # arguments check
        args = row['arguments']['args']
        assert len(args) == 2

        project = args[0]
        url = args[1]
        assert url == 'https://pypi.org/project/%s/' % project

        # kwargs
        kwargs = row['arguments']['kwargs']
        meta_url = kwargs['project_metadata_url']
        assert meta_url == 'https://pypi.org/pypi/%s/json' % project

        assert row['policy'] == 'recurring'
        assert row['priority'] is None
