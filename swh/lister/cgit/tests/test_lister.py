# Copyright (C) 2019-2021 The Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import List

from swh.lister import __version__
from swh.lister.cgit.lister import CGitLister
from swh.lister.pattern import ListerStats


def test_lister_cgit_get_pages_one_page(requests_mock_datadir, swh_scheduler):
    url = "https://git.savannah.gnu.org/cgit/"
    lister_cgit = CGitLister(swh_scheduler, url=url)

    repos: List[List[str]] = list(lister_cgit.get_pages())
    flattened_repos = sum(repos, [])
    assert len(flattened_repos) == 977

    assert flattened_repos[0] == "https://git.savannah.gnu.org/cgit/elisp-es.git/"
    # note the url below is NOT a subpath of /cgit/
    assert (
        flattened_repos[-1] == "https://git.savannah.gnu.org/path/to/yetris.git/"
    )  # noqa
    # note the url below is NOT on the same server
    assert flattened_repos[-2] == "http://example.org/cgit/xstarcastle.git/"


def test_lister_cgit_get_pages_with_pages(requests_mock_datadir, swh_scheduler):
    url = "https://git.tizen/cgit/"
    lister_cgit = CGitLister(swh_scheduler, url=url)

    repos: List[List[str]] = list(lister_cgit.get_pages())
    flattened_repos = sum(repos, [])
    # we should have 16 repos (listed on 3 pages)
    assert len(repos) == 3
    assert len(flattened_repos) == 16


def test_lister_cgit_run(requests_mock_datadir, swh_scheduler):
    """cgit lister supports pagination"""

    url = "https://git.tizen/cgit/"
    lister_cgit = CGitLister(swh_scheduler, url=url)

    stats = lister_cgit.run()

    expected_nb_origins = 16
    assert stats == ListerStats(pages=3, origins=expected_nb_origins)

    # test page parsing
    scheduler_origins = swh_scheduler.get_listed_origins(
        lister_cgit.lister_obj.id
    ).origins
    assert len(scheduler_origins) == expected_nb_origins

    # test listed repositories
    for listed_origin in scheduler_origins:
        assert listed_origin.visit_type == "git"
        assert listed_origin.url.startswith("https://git.tizen")

    # test user agent content
    assert len(requests_mock_datadir.request_history) != 0
    for request in requests_mock_datadir.request_history:
        assert "User-Agent" in request.headers
        user_agent = request.headers["User-Agent"]
        assert "Software Heritage Lister" in user_agent
        assert __version__ in user_agent
