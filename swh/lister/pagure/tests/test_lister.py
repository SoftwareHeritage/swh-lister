# Copyright (C) 2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest

from swh.lister.pagure.lister import PagureLister

expected_origins = {
    "https://pagure.io/10291-testing",
    "https://pagure.io/neuro-sig/20190909-OSB-workshop-presentation",
    "https://pagure.io/neuro-sig/2019-flock-neurofedora",
}


@pytest.mark.parametrize(
    "params", [{"url": "https://pagure.io"}, {"instance": "pagure.io"}]
)
def test_pagure_lister(requests_mock_datadir, swh_scheduler, params):
    lister = PagureLister(**params, scheduler=swh_scheduler, per_page=2)
    res = lister.run()

    assert res.pages == 2
    assert res.origins == 3

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    assert len(scheduler_origins) == len(expected_origins)

    for origin in scheduler_origins:
        assert origin.visit_type == "git"
        assert origin.url in expected_origins
        assert origin.last_update is not None
