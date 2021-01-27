# Copyright (C) 2019-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from unittest.mock import patch

from swh.lister.pattern import ListerStats


def test_ping(swh_scheduler_celery_app, swh_scheduler_celery_worker):
    res = swh_scheduler_celery_app.send_task("swh.lister.pypi.tasks.ping")
    assert res
    res.wait()
    assert res.successful()
    assert res.result == "OK"


@patch("swh.lister.pypi.tasks.PyPILister")
def test_lister(lister, swh_scheduler_celery_app, swh_scheduler_celery_worker):
    # setup the mocked PypiLister
    lister.from_configfile.return_value = lister
    lister.run.return_value = ListerStats(pages=1, origins=0)

    res = swh_scheduler_celery_app.send_task("swh.lister.pypi.tasks.PyPIListerTask")
    assert res
    res.wait()
    assert res.successful()

    lister.from_configfile.assert_called_once_with()
    lister.run.assert_called_once_with()
