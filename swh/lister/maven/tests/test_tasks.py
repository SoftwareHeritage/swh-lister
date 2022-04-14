# Copyright (C) 2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest

from swh.lister.pattern import ListerStats


def test_ping(swh_scheduler_celery_app, swh_scheduler_celery_worker):
    res = swh_scheduler_celery_app.send_task("swh.lister.maven.tasks.ping")
    assert res
    res.wait()
    assert res.successful()
    assert res.result == "OK"


@pytest.mark.parametrize(
    "task_name,incremental",
    [("IncrementalMavenLister", True), ("FullMavenLister", False)],
)
def test_task_lister_maven(
    task_name,
    incremental,
    swh_scheduler_celery_app,
    swh_scheduler_celery_worker,
    mocker,
):
    lister = mocker.patch("swh.lister.maven.tasks.MavenLister")
    lister.from_configfile.return_value = lister
    lister.run.return_value = ListerStats(pages=10, origins=500)

    kwargs = dict(
        url="https://repo1.maven.org/maven2/", index_url="http://indexes/export.fld"
    )
    res = swh_scheduler_celery_app.send_task(
        f"swh.lister.maven.tasks.{task_name}",
        kwargs=kwargs,
    )
    assert res
    res.wait()
    assert res.successful()

    lister.from_configfile.assert_called_once_with(incremental=incremental, **kwargs)
    lister.run.assert_called_once_with()
