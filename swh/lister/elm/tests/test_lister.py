# Copyright (C) 2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.lister.elm.lister import ElmLister

expected_origins = [
    "https://github.com/STTR13/ziplist",
    "https://github.com/elm/bytes",
    "https://github.com/cuducos/elm-format-number",
]


def test_elm_lister(datadir, requests_mock_datadir, swh_scheduler):
    lister = ElmLister(scheduler=swh_scheduler)
    res = lister.run()

    assert res.pages == 1
    assert res.origins == 1 + 1 + 1

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    assert len(scheduler_origins) == len(expected_origins)
    assert {
        (
            scheduled.visit_type,
            scheduled.url,
            scheduled.last_update,
        )
        for scheduled in scheduler_origins
    } == {("git", expected, None) for expected in expected_origins}
