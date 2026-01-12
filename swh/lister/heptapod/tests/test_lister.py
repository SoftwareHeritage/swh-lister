# Copyright (C) 2017-2024 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging

from swh.lister import USER_AGENT_TEMPLATE
from swh.lister.gitlab.tests.test_lister import api_url, gitlab_page_response
from swh.lister.heptapod.lister import HeptapodLister
from swh.lister.pattern import ListerStats

logger = logging.getLogger(__name__)


def _match_request(request):
    return (
        request.headers.get("User-Agent")
        == USER_AGENT_TEMPLATE % HeptapodLister.LISTER_NAME
    )


def test_lister_heptapod(datadir, swh_scheduler, requests_mock):
    """Heptapod lister happily lists hg, hg_git as hg and git origins"""
    instance = "foss.heptapod.net"
    lister = HeptapodLister(swh_scheduler, url=api_url(instance), instance=instance)

    response = gitlab_page_response(datadir, instance, 1)

    requests_mock.get(
        lister.page_url(),
        [{"json": response}],
        additional_matcher=_match_request,
    )

    listed_result = lister.run()
    expected_nb_origins = len(response)

    for entry in response:
        assert entry["vcs_type"] in ("hg", "hg_git")

    assert listed_result == ListerStats(pages=1, origins=expected_nb_origins)

    scheduler_origins = lister.scheduler.get_listed_origins(
        lister.lister_obj.id
    ).results
    assert len(scheduler_origins) == expected_nb_origins

    for listed_origin in scheduler_origins:
        assert listed_origin.visit_type == "hg"
        assert listed_origin.url.startswith(f"https://{instance}")
        assert listed_origin.last_update is not None
