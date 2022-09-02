# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.lister.pubdev.lister import PubDevLister

expected_origins = {
    "https://pub.dev/packages/Autolinker",
    "https://pub.dev/packages/Babylon",
}


def test_pubdev_lister(datadir, requests_mock_datadir, swh_scheduler):
    lister = PubDevLister(scheduler=swh_scheduler)
    res = lister.run()

    assert res.pages == 1
    assert res.origins == 2

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    assert len(scheduler_origins) == len(expected_origins)

    for origin in scheduler_origins:
        assert origin.visit_type == "pubdev"
        assert origin.url in expected_origins
