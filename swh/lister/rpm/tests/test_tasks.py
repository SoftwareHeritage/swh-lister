# Copyright (C) 2022-2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


from swh.lister.pattern import ListerStats

from .test_lister import FEDORA_ARCHIVE_URL, FEDORA_INDEX_URL_TEMPLATES, FEDORA_URL


def test_ping(swh_scheduler_celery_app, swh_scheduler_celery_worker):
    res = swh_scheduler_celery_app.send_task("swh.lister.rpm.tasks.ping")
    assert res
    res.wait()
    assert res.successful()
    assert res.result == "OK"


LISTER_KWARGS = dict(
    url=FEDORA_URL,
    instance="fedora",
    rpm_src_data=[
        {
            "base_url": FEDORA_ARCHIVE_URL,
            "releases": ["36"],
            "components": ["Everything"],
            "index_url_templates": FEDORA_INDEX_URL_TEMPLATES,
        }
    ],
)


def test_full_listing(swh_scheduler_celery_app, swh_scheduler_celery_worker, mocker):
    lister = mocker.patch("swh.lister.rpm.tasks.RPMLister")
    lister.from_configfile.return_value = lister
    lister.run.return_value = ListerStats(pages=10, origins=500)

    res = swh_scheduler_celery_app.send_task(
        "swh.lister.rpm.tasks.FullRPMLister",
        kwargs=LISTER_KWARGS,
    )
    assert res
    res.wait()
    assert res.successful()

    lister.from_configfile.assert_called_once_with(**LISTER_KWARGS)
    lister.run.assert_called_once_with()


def test_incremental_listing(
    swh_scheduler_celery_app, swh_scheduler_celery_worker, mocker
):
    lister = mocker.patch("swh.lister.rpm.tasks.RPMLister")
    lister.from_configfile.return_value = lister
    lister.run.return_value = ListerStats(pages=10, origins=500)

    res = swh_scheduler_celery_app.send_task(
        "swh.lister.rpm.tasks.IncrementalRPMLister",
        kwargs=LISTER_KWARGS,
    )
    assert res
    res.wait()
    assert res.successful()

    lister.from_configfile.assert_called_once_with(**LISTER_KWARGS, incremental=True)
    lister.run.assert_called_once_with()
