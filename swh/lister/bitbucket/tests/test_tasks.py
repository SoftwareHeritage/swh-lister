# Copyright (C) 2019-2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from unittest.mock import patch

from swh.lister.pattern import ListerStats


def test_ping(swh_scheduler_celery_app, swh_scheduler_celery_worker):
    res = swh_scheduler_celery_app.send_task("swh.lister.bitbucket.tasks.ping")
    assert res
    res.wait()
    assert res.successful()
    assert res.result == "OK"


@patch("swh.lister.bitbucket.tasks.BitbucketLister")
def test_incremental_listing(
    lister, swh_scheduler_celery_app, swh_scheduler_celery_worker
):
    lister.from_configfile.return_value = lister
    lister.run.return_value = ListerStats(pages=5, origins=5000)

    res = swh_scheduler_celery_app.send_task(
        "swh.lister.bitbucket.tasks.IncrementalBitBucketLister",
        kwargs=dict(
            page_size=100,
            username="username",
            password="password",
        ),
    )
    assert res
    res.wait()
    assert res.successful()

    lister.run.assert_called_once()


@patch("swh.lister.bitbucket.tasks.BitbucketLister")
def test_full_listing(lister, swh_scheduler_celery_app, swh_scheduler_celery_worker):
    lister.from_configfile.return_value = lister
    lister.run.return_value = ListerStats(pages=5, origins=5000)

    res = swh_scheduler_celery_app.send_task(
        "swh.lister.bitbucket.tasks.FullBitBucketRelister",
        kwargs=dict(
            page_size=100,
            username="username",
            password="password",
        ),
    )
    assert res
    res.wait()
    assert res.successful()

    lister.run.assert_called_once()
