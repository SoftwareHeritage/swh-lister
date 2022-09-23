# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.lister.nuget.lister import NugetLister

expected_origins = ["https://github.com/sillsdev/libpalaso.git"]


def test_nuget_lister(datadir, requests_mock_datadir, swh_scheduler):
    lister = NugetLister(scheduler=swh_scheduler)
    res = lister.run()

    assert res.pages == 2
    assert res.origins == 1

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    assert len(scheduler_origins) == len(expected_origins)

    assert [
        (
            scheduled.visit_type,
            scheduled.url,
        )
        for scheduled in sorted(scheduler_origins, key=lambda scheduled: scheduled.url)
    ] == [
        (
            "git",
            url,
        )
        for url in expected_origins
    ]
