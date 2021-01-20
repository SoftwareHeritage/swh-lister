# Copyright (C) 2019-2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from unittest.mock import patch

from swh.lister.pattern import ListerStats


def test_ping(swh_scheduler_celery_app, swh_scheduler_celery_worker):
    res = swh_scheduler_celery_app.send_task("swh.lister.debian.tasks.ping")
    assert res
    res.wait()
    assert res.successful()
    assert res.result == "OK"


@patch("swh.lister.debian.tasks.DebianLister")
def test_lister(lister, swh_scheduler_celery_app, swh_scheduler_celery_worker):
    # setup the mocked DebianLister
    lister.from_configfile.return_value = lister
    stats = ListerStats(pages=12, origins=35618)
    lister.run.return_value = stats

    kwargs = dict(
        mirror_url="http://www-ftp.lip6.fr/pub/linux/distributions/Ubuntu/archive/",
        distribution="Ubuntu",
        suites=["xenial", "bionic", "focal"],
        components=["main", "multiverse", "restricted", "universe"],
    )

    res = swh_scheduler_celery_app.send_task(
        "swh.lister.debian.tasks.DebianListerTask", kwargs=kwargs
    )
    assert res
    res.wait()
    assert res.successful()

    lister.from_configfile.assert_called_once_with(**kwargs)
    lister.run.assert_called_once_with()

    assert res.result == stats.dict()
