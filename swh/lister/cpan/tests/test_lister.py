# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information
from swh.lister.cpan.lister import CpanLister

expected_origins = [
    "https://metacpan.org/dist/App-Booklist",
    "https://metacpan.org/dist/EuclideanRhythm",
    "https://metacpan.org/dist/EventSource-Server",
    "https://metacpan.org/dist/Getopt_Auto",
    "https://metacpan.org/dist/Interchange6",
    "https://metacpan.org/dist/Internals-CountObjects",
    "https://metacpan.org/dist/openerserver_perl-master",
]


def test_cpan_lister(datadir, requests_mock_datadir_visits, swh_scheduler):
    lister = CpanLister(scheduler=swh_scheduler)
    res = lister.run()

    assert res.pages == 3
    assert res.origins == 4 + 3 + 0

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    assert len(scheduler_origins) == len(expected_origins)

    for origin in scheduler_origins:
        assert origin.visit_type == "cpan"
        assert origin.url in expected_origins
