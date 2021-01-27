from time import sleep
from unittest.mock import call, patch

from celery.result import GroupResult

from swh.lister.github.lister import GitHubListerState
from swh.lister.pattern import ListerStats


def test_ping(swh_scheduler_celery_app, swh_scheduler_celery_worker):
    res = swh_scheduler_celery_app.send_task("swh.lister.github.tasks.ping")
    assert res
    res.wait()
    assert res.successful()
    assert res.result == "OK"


@patch("swh.lister.github.tasks.GitHubLister")
def test_incremental(lister, swh_scheduler_celery_app, swh_scheduler_celery_worker):
    # setup the mocked GitHubLister
    lister.from_configfile.return_value = lister
    lister.state = GitHubListerState()
    lister.run.return_value = ListerStats(pages=5, origins=5000)

    res = swh_scheduler_celery_app.send_task(
        "swh.lister.github.tasks.IncrementalGitHubLister"
    )
    assert res
    res.wait()
    assert res.successful()

    lister.from_configfile.assert_called_once_with()


@patch("swh.lister.github.tasks.GitHubLister")
def test_range(lister, swh_scheduler_celery_app, swh_scheduler_celery_worker):
    # setup the mocked GitHubLister
    lister.return_value = lister
    lister.from_configfile.return_value = lister
    lister.run.return_value = ListerStats(pages=5, origins=5000)

    res = swh_scheduler_celery_app.send_task(
        "swh.lister.github.tasks.RangeGitHubLister",
        kwargs=dict(first_id=12, last_id=42),
    )
    assert res
    res.wait()
    assert res.successful()

    lister.from_configfile.assert_called_once_with(first_id=12, last_id=42)
    lister.run.assert_called_once_with()


@patch("swh.lister.github.tasks.GitHubLister")
def test_lister_full(lister, swh_scheduler_celery_app, swh_scheduler_celery_worker):
    last_index = 1000000
    expected_bounds = list(range(0, last_index + 1, 100000))
    if expected_bounds[-1] != last_index:
        expected_bounds.append(last_index)

    # setup the mocked GitHubLister
    lister.state = GitHubListerState(last_seen_id=last_index)
    lister.from_configfile.return_value = lister
    lister.run.return_value = ListerStats(pages=10, origins=10000)

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

    # pulling the state out of the database
    assert lister.from_configfile.call_args_list[0] == call()

    # Calls for each of the ranges
    range_calls = lister.from_configfile.call_args_list[1:]
    # Check exhaustivity of the range calls
    assert sorted(range_calls, key=lambda c: c[1]["first_id"]) == [
        call(first_id=f, last_id=l)
        for f, l in zip(expected_bounds[:-1], expected_bounds[1:])
    ]
