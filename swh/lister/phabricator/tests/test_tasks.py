# Copyright (C) 2019-2021 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from unittest.mock import patch

from swh.lister.pattern import ListerStats


def test_ping(swh_scheduler_celery_app, swh_scheduler_celery_worker):
    res = swh_scheduler_celery_app.send_task("swh.lister.phabricator.tasks.ping")
    assert res
    res.wait()
    assert res.successful()
    assert res.result == "OK"


@patch("swh.lister.phabricator.tasks.PhabricatorLister")
def test_phabricator_lister_task(
    lister, swh_scheduler_celery_app, swh_scheduler_celery_worker
):
    # setup the mocked PhabricatorLister
    lister.from_configfile.return_value = lister
    lister_stats = ListerStats(pages=2, origins=200)
    lister.run.return_value = lister_stats

    task_params = {
        "url": "https://forge.softwareheritage.org",
        "instance": "swh",
        "api_token": None,
    }

    res = swh_scheduler_celery_app.send_task(
        "swh.lister.phabricator.tasks.FullPhabricatorLister", kwargs=task_params
    )
    assert res
    res.wait()
    assert res.successful()
    assert res.result == lister_stats.dict()

    lister.from_configfile.assert_called_once_with(**task_params)
