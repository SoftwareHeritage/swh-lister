# Copyright (C) 2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from unittest.mock import patch


def test_ping(swh_app, celery_session_worker):
    res = swh_app.send_task(
        'swh.lister.debian.tasks.ping')
    assert res
    res.wait()
    assert res.successful()
    assert res.result == 'OK'


@patch('swh.lister.debian.tasks.DebianLister')
def test_lister(lister, swh_app, celery_session_worker):
    # setup the mocked DebianLister
    lister.return_value = lister
    lister.run.return_value = None

    res = swh_app.send_task(
        'swh.lister.debian.tasks.DebianListerTask', ('stretch',))
    assert res
    res.wait()
    assert res.successful()

    lister.assert_called_once_with(distribution='stretch')
    lister.run.assert_called_once_with()
