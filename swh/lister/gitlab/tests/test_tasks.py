# Copyright (C) 2019-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest

from swh.lister.pattern import ListerStats


def test_ping(swh_scheduler_celery_app, swh_scheduler_celery_worker):
    res = swh_scheduler_celery_app.send_task("swh.lister.gitlab.tasks.ping")
    assert res
    res.wait()
    assert res.successful()
    assert res.result == "OK"


@pytest.mark.parametrize(
    "task_name,incremental",
    [("IncrementalGitLabLister", True), ("FullGitLabRelister", False)],
)
def test_task_lister_gitlab(
    task_name,
    incremental,
    swh_scheduler_celery_app,
    swh_scheduler_celery_worker,
    mocker,
):
    stats = ListerStats(pages=10, origins=200)
    mock_lister = mocker.patch("swh.lister.gitlab.tasks.GitLabLister")
    mock_lister.from_configfile.return_value = mock_lister
    mock_lister.run.return_value = ListerStats(pages=10, origins=200)

    kwargs = dict(url="https://gitweb.torproject.org/")
    res = swh_scheduler_celery_app.send_task(
        f"swh.lister.gitlab.tasks.{task_name}", kwargs=kwargs,
    )
    assert res
    res.wait()
    assert res.successful()

    mock_lister.from_configfile.assert_called_once_with(
        incremental=incremental, **kwargs
    )
    mock_lister.run.assert_called_once_with()
    assert res.result == stats.dict()
