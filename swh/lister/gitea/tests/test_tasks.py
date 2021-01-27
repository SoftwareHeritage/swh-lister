# Copyright (C) 2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from unittest.mock import patch

from swh.lister.pattern import ListerStats


def test_ping(swh_scheduler_celery_app, swh_scheduler_celery_worker):
    res = swh_scheduler_celery_app.send_task("swh.lister.gitea.tasks.ping")
    assert res
    res.wait()
    assert res.successful()
    assert res.result == "OK"


@patch("swh.lister.gitea.tasks.GiteaLister")
def test_full_listing(lister, swh_scheduler_celery_app, swh_scheduler_celery_worker):
    lister.from_configfile.return_value = lister
    lister.run.return_value = ListerStats(pages=10, origins=500)

    kwargs = dict(url="https://try.gitea.io/api/v1")
    res = swh_scheduler_celery_app.send_task(
        "swh.lister.gitea.tasks.FullGiteaRelister", kwargs=kwargs,
    )
    assert res
    res.wait()
    assert res.successful()

    actual_kwargs = dict(**kwargs, instance=None, api_token=None, page_size=None)

    lister.from_configfile.assert_called_once_with(**actual_kwargs)
    lister.run.assert_called_once_with()


@patch("swh.lister.gitea.tasks.GiteaLister")
def test_full_listing_params(
    lister, swh_scheduler_celery_app, swh_scheduler_celery_worker
):
    lister.from_configfile.return_value = lister
    lister.run.return_value = ListerStats(pages=10, origins=500)

    kwargs = dict(
        url="https://0xacab.org/api/v4",
        instance="0xacab",
        api_token="test",
        page_size=50,
    )
    res = swh_scheduler_celery_app.send_task(
        "swh.lister.gitea.tasks.FullGiteaRelister", kwargs=kwargs,
    )
    assert res
    res.wait()
    assert res.successful()

    lister.from_configfile.assert_called_once_with(**kwargs)
    lister.run.assert_called_once_with()
