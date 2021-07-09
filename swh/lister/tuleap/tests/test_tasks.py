# Copyright (C) 2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.lister.pattern import ListerStats


def test_ping(swh_scheduler_celery_app, swh_scheduler_celery_worker):
    res = swh_scheduler_celery_app.send_task("swh.lister.tuleap.tasks.ping")
    assert res
    res.wait()
    assert res.successful()
    assert res.result == "OK"


def test_full_listing(swh_scheduler_celery_app, swh_scheduler_celery_worker, mocker):
    lister = mocker.patch("swh.lister.tuleap.tasks.TuleapLister")
    lister.from_configfile.return_value = lister
    lister.run.return_value = ListerStats(pages=10, origins=500)

    kwargs = dict(url="https://tuleap.net")
    res = swh_scheduler_celery_app.send_task(
        "swh.lister.tuleap.tasks.FullTuleapLister", kwargs=kwargs,
    )
    assert res
    res.wait()
    assert res.successful()

    lister.from_configfile.assert_called_once_with(**kwargs)
    lister.run.assert_called_once_with()


def test_full_listing_params(
    swh_scheduler_celery_app, swh_scheduler_celery_worker, mocker
):
    lister = mocker.patch("swh.lister.tuleap.tasks.TuleapLister")
    lister.from_configfile.return_value = lister
    lister.run.return_value = ListerStats(pages=10, origins=500)

    kwargs = dict(url="https://tuleap.net", instance="tuleap.net",)
    res = swh_scheduler_celery_app.send_task(
        "swh.lister.tuleap.tasks.FullTuleapLister", kwargs=kwargs,
    )
    assert res
    res.wait()
    assert res.successful()

    lister.from_configfile.assert_called_once_with(**kwargs)
    lister.run.assert_called_once_with()
