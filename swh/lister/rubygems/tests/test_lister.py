# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information
from swh.lister.rubygems.lister import RubyGemsLister

expected_origins = [
    "https://rubygems.org/gems/mercurial-ruby",
    "https://rubygems.org/gems/mercurial-wrapper",
    "https://rubygems.org/gems/mercurius",
]


def test_rubygems_lister(datadir, requests_mock_datadir, swh_scheduler):
    lister = RubyGemsLister(scheduler=swh_scheduler)
    res = lister.run()

    assert res.pages == 3
    assert res.origins == 1 + 1 + 1

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    assert len(scheduler_origins) == len(expected_origins)

    for origin in scheduler_origins:
        assert origin.visit_type == "rubygems"
        assert origin.url in expected_origins
