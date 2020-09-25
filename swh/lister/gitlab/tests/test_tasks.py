# Copyright (C) 2019-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from time import sleep
from unittest.mock import call, patch

from celery.result import GroupResult

from swh.lister.gitea.tasks import NBPAGES
from swh.lister.utils import split_range


def test_ping(swh_scheduler_celery_app, swh_scheduler_celery_worker):
    res = swh_scheduler_celery_app.send_task("swh.lister.gitlab.tasks.ping")
    assert res
    res.wait()
    assert res.successful()
    assert res.result == "OK"


@patch("swh.lister.gitlab.tasks.GitLabLister")
def test_incremental(lister, swh_scheduler_celery_app, swh_scheduler_celery_worker):
    # setup the mocked GitlabLister
    lister.return_value = lister
    lister.run.return_value = None
    lister.get_pages_information.return_value = (None, 10, None)

    res = swh_scheduler_celery_app.send_task(
        "swh.lister.gitlab.tasks.IncrementalGitLabLister"
    )
    assert res
    res.wait()
    assert res.successful()

    lister.assert_called_once_with(sort="desc")
    lister.db_last_index.assert_not_called()
    lister.get_pages_information.assert_called_once_with()
    lister.run.assert_called_once_with(min_bound=1, max_bound=10, check_existence=True)


@patch("swh.lister.gitlab.tasks.GitLabLister")
def test_range(lister, swh_scheduler_celery_app, swh_scheduler_celery_worker):
    # setup the mocked GitlabLister
    lister.return_value = lister
    lister.run.return_value = None

    res = swh_scheduler_celery_app.send_task(
        "swh.lister.gitlab.tasks.RangeGitLabLister", kwargs=dict(start=12, end=42)
    )
    assert res
    res.wait()
    assert res.successful()

    lister.assert_called_once_with()
    lister.db_last_index.assert_not_called()
    lister.run.assert_called_once_with(min_bound=12, max_bound=42)


@patch("swh.lister.gitlab.tasks.GitLabLister")
def test_relister(lister, swh_scheduler_celery_app, swh_scheduler_celery_worker):
    total_pages = 85
    # setup the mocked GitlabLister
    lister.return_value = lister
    lister.run.return_value = None
    lister.get_pages_information.return_value = (None, total_pages, None)

    res = swh_scheduler_celery_app.send_task(
        "swh.lister.gitlab.tasks.FullGitLabRelister"
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

    # one by the FullGitlabRelister task
    # + 9 for the RangeGitlabLister subtasks
    assert lister.call_count == 10

    lister.db_last_index.assert_not_called()
    lister.db_partition_indices.assert_not_called()
    lister.get_pages_information.assert_called_once_with()

    # lister.run should have been called once per partition interval
    for min_bound, max_bound in split_range(total_pages, NBPAGES):
        assert (
            call(min_bound=min_bound, max_bound=max_bound) in lister.run.call_args_list
        )


@patch("swh.lister.gitlab.tasks.GitLabLister")
def test_relister_instance(
    lister, swh_scheduler_celery_app, swh_scheduler_celery_worker
):
    total_pages = 85
    # setup the mocked GitlabLister
    lister.return_value = lister
    lister.run.return_value = None
    lister.get_pages_information.return_value = (None, total_pages, None)

    res = swh_scheduler_celery_app.send_task(
        "swh.lister.gitlab.tasks.FullGitLabRelister",
        kwargs=dict(url="https://0xacab.org/api/v4"),
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

    lister.assert_called_with(url="https://0xacab.org/api/v4")

    # one by the FullGitlabRelister task
    # + 9 for the RangeGitlabLister subtasks
    assert lister.call_count == 10

    lister.db_last_index.assert_not_called()
    lister.db_partition_indices.assert_not_called()
    lister.get_pages_information.assert_called_once_with()

    # lister.run should have been called once per partition interval
    for min_bound, max_bound in split_range(total_pages, NBPAGES):
        assert (
            call(min_bound=min_bound, max_bound=max_bound) in lister.run.call_args_list
        )
