# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from unittest.mock import patch

from swh.lister.pattern import ListerStats


def test_ping(swh_scheduler_celery_app, swh_scheduler_celery_worker):
    res = swh_scheduler_celery_app.send_task("swh.lister.hex.tasks.ping")
    assert res
    res.wait()
    assert res.successful()
    assert res.result == "OK"


@patch("swh.lister.hex.tasks.HexLister")
def test_full_listing(lister, swh_scheduler_celery_app, swh_scheduler_celery_worker):
    lister.from_configfile.return_value = lister
    lister.run.return_value = ListerStats(pages=10, origins=500)

    kwargs = dict()
    res = swh_scheduler_celery_app.send_task(
        "swh.lister.hex.tasks.HexListerTask",
        kwargs=kwargs,
    )
    assert res
    res.wait()
    assert res.successful()

    actual_kwargs = dict(**kwargs, instance=None)

    lister.from_configfile.assert_called_once_with(**actual_kwargs)
    lister.run.assert_called_once_with()


@patch("swh.lister.hex.tasks.HexLister")
def test_full_listing_params(
    lister, swh_scheduler_celery_app, swh_scheduler_celery_worker
):
    lister.from_configfile.return_value = lister
    lister.run.return_value = ListerStats(pages=10, origins=500)

    kwargs = dict(instance="hex.pm")
    res = swh_scheduler_celery_app.send_task(
        "swh.lister.hex.tasks.HexListerTask",
        kwargs=kwargs,
    )
    assert res
    res.wait()
    assert res.successful()

    lister.from_configfile.assert_called_once_with(**kwargs)
    lister.run.assert_called_once_with()
