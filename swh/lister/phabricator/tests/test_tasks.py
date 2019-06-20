# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


def test_ping(swh_app, celery_session_worker):
    res = swh_app.send_task(
        'swh.lister.phabricator.tasks.ping')
    assert res
    res.wait()
    assert res.successful()
    assert res.result == 'OK'
