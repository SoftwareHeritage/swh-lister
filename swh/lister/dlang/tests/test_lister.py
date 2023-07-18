# Copyright (C) 2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information
import iso8601

from swh.lister.dlang.lister import DlangLister

expected_origins = [
    {
        "url": "https://github.com/katyukha/TheProcess",
        "last_update": "2023-07-12T14:42:46.231Z",
    },
    {
        "url": "https://gitlab.com/AntonMeep/silly",
        "last_update": "2023-07-12T01:32:31.235Z",
    },
]


def test_dlang_lister(datadir, requests_mock_datadir, swh_scheduler):
    lister = DlangLister(scheduler=swh_scheduler)
    res = lister.run()

    assert res.pages == 1
    assert res.origins == 1 + 1

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    assert len(scheduler_origins) == len(expected_origins)
    assert {
        (
            scheduled.visit_type,
            scheduled.url,
            scheduled.last_update,
        )
        for scheduled in scheduler_origins
    } == {
        ("git", expected["url"], iso8601.parse_date(expected["last_update"]))
        for expected in expected_origins
    }
