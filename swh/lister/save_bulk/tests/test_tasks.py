# Copyright (C) 2024 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.lister.pattern import ListerStats


def test_save_bulk_ping(swh_scheduler_celery_app, swh_scheduler_celery_worker):
    res = swh_scheduler_celery_app.send_task("swh.lister.save_bulk.tasks.ping")
    assert res
    res.wait()
    assert res.successful()
    assert res.result == "OK"


def test_save_bulk_lister_task(
    swh_scheduler_celery_app, swh_scheduler_celery_worker, mocker
):
    lister = mocker.patch("swh.lister.save_bulk.tasks.SaveBulkLister")
    lister.from_configfile.return_value = lister
    lister.run.return_value = ListerStats(pages=1, origins=2)

    kwargs = dict(
        url="https://example.org/origins/list/",
        instance="some-instance",
    )

    res = swh_scheduler_celery_app.send_task(
        "swh.lister.save_bulk.tasks.SaveBulkListerTask",
        kwargs=kwargs,
    )
    assert res
    res.wait()
    assert res.successful()

    lister.from_configfile.assert_called_once_with(**kwargs)
    lister.run.assert_called_once()
