# Copyright (C) 2019-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from time import sleep
from celery.result import GroupResult

from unittest.mock import patch


def test_ping(swh_scheduler_celery_app, swh_scheduler_celery_worker):
    res = swh_scheduler_celery_app.send_task("swh.lister.bitbucket.tasks.ping")
    assert res
    res.wait()
    assert res.successful()
    assert res.result == "OK"


@patch("swh.lister.bitbucket.tasks.BitBucketLister")
def test_incremental(lister, swh_scheduler_celery_app, swh_scheduler_celery_worker):
    # setup the mocked BitbucketLister
    lister.return_value = lister
    lister.db_last_index.return_value = 42
    lister.run.return_value = None

    res = swh_scheduler_celery_app.send_task(
        "swh.lister.bitbucket.tasks.IncrementalBitBucketLister"
    )
    assert res
    res.wait()
    assert res.successful()

    lister.assert_called_once_with()
    lister.db_last_index.assert_called_once_with()
    lister.run.assert_called_once_with(min_bound=42, max_bound=None)


@patch("swh.lister.bitbucket.tasks.BitBucketLister")
def test_range(lister, swh_scheduler_celery_app, swh_scheduler_celery_worker):
    # setup the mocked BitbucketLister
    lister.return_value = lister
    lister.run.return_value = None

    res = swh_scheduler_celery_app.send_task(
        "swh.lister.bitbucket.tasks.RangeBitBucketLister", kwargs=dict(start=12, end=42)
    )
    assert res
    res.wait()
    assert res.successful()

    lister.assert_called_once_with()
    lister.db_last_index.assert_not_called()
    lister.run.assert_called_once_with(min_bound=12, max_bound=42)


@patch("swh.lister.bitbucket.tasks.BitBucketLister")
def test_relister(lister, swh_scheduler_celery_app, swh_scheduler_celery_worker):
    # setup the mocked BitbucketLister
    lister.return_value = lister
    lister.run.return_value = None
    lister.db_partition_indices.return_value = [(i, i + 9) for i in range(0, 50, 10)]

    res = swh_scheduler_celery_app.send_task(
        "swh.lister.bitbucket.tasks.FullBitBucketRelister"
    )
    assert res

    res.wait()
    assert res.successful()

    # retrieve the GroupResult for this task and wait for all the subtasks
    # to complete
    promise_id = res.result
    assert promise_id
    promise = GroupResult.restore(promise_id, app=swh_scheduler_celery_app)
    for i in range(5):
        if promise.ready():
            break
        sleep(1)

    lister.assert_called_with()

    # one by the FullBitbucketRelister task
    # + 5 for the RangeBitbucketLister subtasks
    assert lister.call_count == 6

    lister.db_last_index.assert_not_called()
    lister.db_partition_indices.assert_called_once_with(10000)

    # lister.run should have been called once per partition interval
    for i in range(5):
        assert (
            dict(min_bound=10 * i, max_bound=10 * i + 9),
        ) in lister.run.call_args_list
