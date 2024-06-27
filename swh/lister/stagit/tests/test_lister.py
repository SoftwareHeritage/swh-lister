# Copyright (C) 2023-2024 The Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os
from typing import List

import pytest

from swh.lister import __version__
from swh.lister.pattern import ListerStats
from swh.lister.stagit.lister import StagitLister, _parse_date

MAIN_INSTANCE = "codemadness.org"
MAIN_INSTANCE_URL = f"https://{MAIN_INSTANCE}/git"


def test_lister_stagit_instantiate(swh_scheduler):
    """Build a lister with either an url or an instance is supported."""
    url = MAIN_INSTANCE_URL
    lister = StagitLister(swh_scheduler, url=url)
    assert lister is not None
    assert lister.url == url

    assert StagitLister(swh_scheduler, instance=MAIN_INSTANCE) is not None
    assert lister is not None
    assert lister.url == url


def test_lister_stagit_fail_to_instantiate(swh_scheduler):
    """Build a lister without its url nor its instance should raise"""
    # ... It will raise without any of those
    with pytest.raises(ValueError, match="'url' or 'instance'"):
        StagitLister(swh_scheduler)


def test_lister_stagit_get_pages(requests_mock_datadir, swh_scheduler):
    """Computing the number of pages scrapped during a listing."""
    url = MAIN_INSTANCE_URL
    lister_stagit = StagitLister(swh_scheduler, url=url)

    expected_nb_origins = 4

    repos: List[List[str]] = list(lister_stagit.get_pages())
    flattened_repos = sum(repos, [])
    assert len(flattened_repos) == expected_nb_origins

    for listed_url in flattened_repos:
        assert MAIN_INSTANCE in listed_url["url"]


def test_lister_stagit_run(requests_mock_datadir, swh_scheduler):
    """Gitweb lister nominal listing case."""

    url = MAIN_INSTANCE_URL
    lister_stagit = StagitLister(swh_scheduler, url=url)

    stats = lister_stagit.run()

    expected_nb_origins = 4  # main page will get filtered out
    assert stats == ListerStats(pages=1, origins=expected_nb_origins)

    # test page parsing
    scheduler_origins = swh_scheduler.get_listed_origins(
        lister_stagit.lister_obj.id
    ).results
    assert len(scheduler_origins) == expected_nb_origins

    # test listed repositories
    for listed_origin in scheduler_origins:
        assert listed_origin.visit_type == "git"
        assert MAIN_INSTANCE in listed_origin.url
        assert listed_origin.last_update is not None

    # test user agent content
    for request in requests_mock_datadir.request_history:
        assert "User-Agent" in request.headers
        user_agent = request.headers["User-Agent"]
        assert "Software Heritage stagit lister" in user_agent
        assert __version__ in user_agent


def test_lister_stagit_get_pages_with_pages_and_retry(
    requests_mock_datadir, requests_mock, datadir, mocker, swh_scheduler
):
    """Rate limited page are tested back after some time so ingestion can proceed."""
    url = MAIN_INSTANCE_URL
    with open(os.path.join(datadir, f"https_{MAIN_INSTANCE}/git"), "rb") as page:
        requests_mock.get(
            url,
            [
                {"content": None, "status_code": 429},
                {"content": None, "status_code": 429},
                {"content": page.read(), "status_code": 200},
            ],
        )

        lister_stagit = StagitLister(swh_scheduler, url=url)

        pages: List[List[str]] = list(lister_stagit.get_pages())
        flattened_repos = sum(pages, [])
        assert len(pages) == 1
        assert len(flattened_repos) == 4


def test_lister_stagit_get_origin_from_repo_failing(
    swh_scheduler, requests_mock_datadir
):
    """Instances whose summary does not return anything are filtered out."""
    # This instance has some more origins which no longer returns their summary
    lister_stagit = StagitLister(swh_scheduler, url=f"https://{MAIN_INSTANCE}/foobar")

    stats = lister_stagit.run()

    # so they are filtered out, only the 7 we know are thus listed
    expected_nb_origins = 4
    assert stats == ListerStats(pages=1, origins=expected_nb_origins)


def test__parse_date():
    assert _parse_date(None) is None
    assert _parse_date("No commits") is None

    date = _parse_date("2022-08-26 12:48")
    assert date is not None
    assert date.tzinfo is not None
