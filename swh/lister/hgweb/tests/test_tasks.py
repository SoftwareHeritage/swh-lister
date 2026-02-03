# Copyright (C) 2026  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.lister.pattern import ListerStats


def test_hgweb_lister_task(
    swh_scheduler_celery_app, swh_scheduler_celery_worker, mocker
):
    # setup the mocked HgwebLister
    lister = mocker.patch("swh.lister.hgweb.tasks.HgwebLister")
    lister.from_configfile.return_value = lister
    lister.run.return_value = ListerStats(pages=10, origins=500)

    kwargs = dict(
        url="https://repo.mercurial-scm.org/",
        instance="repo.mercurial-scm.org",
        max_pages=1,
    )

    res = swh_scheduler_celery_app.send_task(
        "swh.lister.hgweb.tasks.HgwebListerTask",
        kwargs=kwargs,
    )
    assert res
    res.wait()
    assert res.successful()

    lister.from_configfile.assert_called_once_with(**kwargs)
    lister.run.assert_called_once_with()
