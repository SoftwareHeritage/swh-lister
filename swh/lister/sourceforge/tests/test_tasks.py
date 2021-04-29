# Copyright (C) 2019-2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.lister.pattern import ListerStats


def test_sourceforge_ping(swh_scheduler_celery_app, swh_scheduler_celery_worker):
    res = swh_scheduler_celery_app.send_task("swh.lister.sourceforge.tasks.ping")
    assert res
    res.wait()
    assert res.successful()
    assert res.result == "OK"


def test_sourceforge_full_lister_task(
    swh_scheduler_celery_app, swh_scheduler_celery_worker, mocker
):
    stats = ListerStats(pages=10, origins=900)
    mock_lister = mocker.patch("swh.lister.sourceforge.tasks.SourceForgeLister")
    mock_lister.from_configfile.return_value = mock_lister
    mock_lister.run.return_value = stats

    res = swh_scheduler_celery_app.send_task(
        "swh.lister.sourceforge.tasks.FullSourceForgeLister"
    )
    assert res
    res.wait()
    assert res.successful()

    mock_lister.from_configfile.assert_called_once()
    mock_lister.run.assert_called_once()
    assert res.result == stats.dict()
