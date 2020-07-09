# Copyright (C) 2019-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from unittest.mock import patch


def test_ping(swh_scheduler_celery_app, swh_scheduler_celery_worker):
    res = swh_scheduler_celery_app.send_task("swh.lister.cran.tasks.ping")
    assert res
    res.wait()
    assert res.successful()
    assert res.result == "OK"


@patch("swh.lister.cran.tasks.CRANLister")
def test_lister(lister, swh_scheduler_celery_app, swh_scheduler_celery_worker):
    # setup the mocked CRANLister
    lister.return_value = lister
    lister.run.return_value = None

    res = swh_scheduler_celery_app.send_task("swh.lister.cran.tasks.CRANListerTask")
    assert res
    res.wait()
    assert res.successful()

    lister.assert_called_once_with()
    lister.db_last_index.assert_not_called()
    lister.run.assert_called_once_with()
