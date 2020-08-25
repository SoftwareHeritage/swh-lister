# Copyright (C) 2019-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from contextlib import contextmanager
from unittest.mock import patch


@contextmanager
def mock_save(lister):
    yield


def test_ping(swh_scheduler_celery_app, swh_scheduler_celery_worker):
    res = swh_scheduler_celery_app.send_task("swh.lister.npm.tasks.ping")
    assert res
    res.wait()
    assert res.successful()
    assert res.result == "OK"


@patch("swh.lister.npm.tasks.save_registry_state")
@patch("swh.lister.npm.tasks.NpmLister")
def test_lister(lister, save, swh_scheduler_celery_app, swh_scheduler_celery_worker):
    # setup the mocked NpmLister
    lister.return_value = lister
    lister.run.return_value = None
    save.side_effect = mock_save

    res = swh_scheduler_celery_app.send_task("swh.lister.npm.tasks.NpmListerTask")
    assert res
    res.wait()
    assert res.successful()

    lister.assert_called_once_with()
    lister.run.assert_called_once_with()


@patch("swh.lister.npm.tasks.save_registry_state")
@patch("swh.lister.npm.tasks.get_last_update_seq")
@patch("swh.lister.npm.tasks.NpmIncrementalLister")
def test_incremental(
    lister, seq, save, swh_scheduler_celery_app, swh_scheduler_celery_worker
):
    # setup the mocked NpmLister
    lister.return_value = lister
    lister.run.return_value = None
    seq.return_value = 42
    save.side_effect = mock_save

    res = swh_scheduler_celery_app.send_task(
        "swh.lister.npm.tasks.NpmIncrementalListerTask"
    )
    assert res
    res.wait()
    assert res.successful()

    lister.assert_called_once_with()
    seq.assert_called_once_with(lister)
    lister.run.assert_called_once_with(min_bound=42)
