# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from unittest.mock import patch

from swh.lister.pattern import ListerStats


def test_ping(swh_scheduler_celery_app, swh_scheduler_celery_worker):
    res = swh_scheduler_celery_app.send_task("swh.lister.fedora.tasks.ping")
    assert res
    res.wait()
    assert res.successful()
    assert res.result == "OK"


@patch("swh.lister.fedora.tasks.FedoraLister")
def test_full_listing(lister, swh_scheduler_celery_app, swh_scheduler_celery_worker):
    lister.from_configfile.return_value = lister
    lister.run.return_value = ListerStats(pages=10, origins=500)

    kwargs = dict(
        url="https://archives.fedoraproject.org/pub/archive/fedora/linux/releases/"
    )
    res = swh_scheduler_celery_app.send_task(
        "swh.lister.fedora.tasks.FullFedoraRelister",
        kwargs=kwargs,
    )
    assert res
    res.wait()
    assert res.successful()

    lister.from_configfile.assert_called_once_with(**kwargs)
    lister.run.assert_called_once_with()


@patch("swh.lister.fedora.tasks.FedoraLister")
def test_full_listing_params(
    lister, swh_scheduler_celery_app, swh_scheduler_celery_worker
):
    lister.from_configfile.return_value = lister
    lister.run.return_value = ListerStats(pages=10, origins=500)

    kwargs = dict(
        url="https://archives.fedoraproject.org/pub/archive/fedora/linux/releases/",
        instance="archives.fedoraproject.org",
        releases=["36"],
    )
    res = swh_scheduler_celery_app.send_task(
        "swh.lister.fedora.tasks.FullFedoraRelister",
        kwargs=kwargs,
    )
    assert res
    res.wait()
    assert res.successful()

    lister.from_configfile.assert_called_once_with(**kwargs)
    lister.run.assert_called_once_with()
