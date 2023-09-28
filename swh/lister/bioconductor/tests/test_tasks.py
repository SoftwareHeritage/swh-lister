# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from unittest.mock import patch

from swh.lister.pattern import ListerStats


def test_ping(swh_scheduler_celery_app, swh_scheduler_celery_worker):
    res = swh_scheduler_celery_app.send_task("swh.lister.bioconductor.tasks.ping")
    assert res
    res.wait()
    assert res.successful()
    assert res.result == "OK"


@patch("swh.lister.bioconductor.tasks.BioconductorLister")
def test_full_listing(lister, swh_scheduler_celery_app, swh_scheduler_celery_worker):
    lister.from_configfile.return_value = lister
    lister.run.return_value = ListerStats(pages=10, origins=500)

    kwargs = dict(url="https://www.bioconductor.org")
    res = swh_scheduler_celery_app.send_task(
        "swh.lister.bioconductor.tasks.BioconductorListerTask",
        kwargs=kwargs,
    )
    assert res
    res.wait()
    assert res.successful()

    lister.from_configfile.assert_called_once_with(**kwargs)
    lister.run.assert_called_once_with()


@patch("swh.lister.bioconductor.tasks.BioconductorLister")
def test_incremental_listing(
    lister, swh_scheduler_celery_app, swh_scheduler_celery_worker
):
    lister.from_configfile.return_value = lister
    lister.run.return_value = ListerStats(pages=10, origins=500)

    kwargs = dict(url="https://www.bioconductor.org")
    res = swh_scheduler_celery_app.send_task(
        "swh.lister.bioconductor.tasks.BioconductorIncrementalListerTask",
        kwargs=kwargs,
    )
    assert res
    res.wait()
    assert res.successful()

    kwargs["incremental"] = True

    lister.from_configfile.assert_called_once_with(**kwargs)
    lister.run.assert_called_once_with()


@patch("swh.lister.bioconductor.tasks.BioconductorLister")
def test_full_listing_with_params(
    lister, swh_scheduler_celery_app, swh_scheduler_celery_worker
):
    lister.from_configfile.return_value = lister
    lister.run.return_value = ListerStats(pages=10, origins=500)

    kwargs = dict(
        url="https://www.bioconductor.org",
        instance="bioconductor-test",
        releases=["3.7"],
        categories=["bioc", "workflows"],
    )
    res = swh_scheduler_celery_app.send_task(
        "swh.lister.bioconductor.tasks.BioconductorListerTask",
        kwargs=kwargs,
    )
    assert res
    res.wait()
    assert res.successful()

    lister.from_configfile.assert_called_once_with(**kwargs)
    lister.run.assert_called_once_with()
