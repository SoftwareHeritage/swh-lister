from time import sleep
from unittest.mock import patch

from celery.result import GroupResult


def test_ping(swh_scheduler_celery_app, swh_scheduler_celery_worker):
    res = swh_scheduler_celery_app.send_task("swh.lister.github.tasks.ping")
    assert res
    res.wait()
    assert res.successful()
    assert res.result == "OK"


@patch("swh.lister.github.tasks.GitHubLister")
def test_incremental(lister, swh_scheduler_celery_app, swh_scheduler_celery_worker):
    # setup the mocked GitHubLister
    lister.return_value = lister
    lister.db_last_index.return_value = 42
    lister.run.return_value = None

    res = swh_scheduler_celery_app.send_task(
        "swh.lister.github.tasks.IncrementalGitHubLister"
    )
    assert res
    res.wait()
    assert res.successful()

    lister.assert_called_once_with()
    lister.db_last_index.assert_called_once_with()
    lister.run.assert_called_once_with(min_bound=42, max_bound=None)


@patch("swh.lister.github.tasks.GitHubLister")
def test_range(lister, swh_scheduler_celery_app, swh_scheduler_celery_worker):
    # setup the mocked GitHubLister
    lister.return_value = lister
    lister.run.return_value = None

    res = swh_scheduler_celery_app.send_task(
        "swh.lister.github.tasks.RangeGitHubLister", kwargs=dict(start=12, end=42)
    )
    assert res
    res.wait()
    assert res.successful()

    lister.assert_called_once_with()
    lister.db_last_index.assert_not_called()
    lister.run.assert_called_once_with(min_bound=12, max_bound=42)


@patch("swh.lister.github.tasks.GitHubLister")
def test_relister(lister, swh_scheduler_celery_app, swh_scheduler_celery_worker):
    # setup the mocked GitHubLister
    lister.return_value = lister
    lister.run.return_value = None
    lister.db_partition_indices.return_value = [(i, i + 9) for i in range(0, 50, 10)]

    res = swh_scheduler_celery_app.send_task(
        "swh.lister.github.tasks.FullGitHubRelister"
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

    # one by the FullGitHubRelister task
    # + 5 for the RangeGitHubLister subtasks
    assert lister.call_count == 6

    lister.db_last_index.assert_not_called()
    lister.db_partition_indices.assert_called_once_with(10000)

    # lister.run should have been called once per partition interval
    for i in range(5):
        # XXX inconsistent behavior: max_bound is INCLUDED here
        assert (
            dict(min_bound=10 * i, max_bound=10 * i + 9),
        ) in lister.run.call_args_list
