# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information
from swh.lister.bower.lister import BowerLister

expected_origins = [
    {"name": "font-awesome", "url": "https://github.com/FortAwesome/Font-Awesome.git"},
    {"name": "redux", "url": "https://github.com/reactjs/redux.git"},
    {"name": "vue", "url": "https://github.com/vuejs/vue.git"},
]


def test_bower_lister(datadir, requests_mock_datadir, swh_scheduler):
    lister = BowerLister(scheduler=swh_scheduler)
    res = lister.run()

    assert res.pages == 1
    assert res.origins == 1 + 1 + 1

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    assert len(scheduler_origins) == len(expected_origins)

    assert {
        (
            scheduled.visit_type,
            scheduled.url,
        )
        for scheduled in scheduler_origins
    } == {
        (
            "git",
            expected["url"],
        )
        for expected in expected_origins
    }
