# Copyright (C) 2023-2024 The Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os
from typing import List

import pytest

from swh.lister import __version__
from swh.lister.gitiles.lister import GitilesLister
from swh.lister.pattern import ListerStats

MAIN_INSTANCE = "android.googlesource.com"
MAIN_INSTANCE_URL = f"https://{MAIN_INSTANCE}"


def test_lister_gitiles_instantiate(swh_scheduler):
    """Build a lister with either an url or an instance is supported."""
    url = MAIN_INSTANCE_URL
    lister = GitilesLister(swh_scheduler, url=url)
    assert lister is not None
    assert lister.url == url

    assert GitilesLister(swh_scheduler, instance=MAIN_INSTANCE) is not None
    assert lister is not None
    assert lister.url == url


def test_lister_gitiles_fail_to_instantiate(swh_scheduler):
    """Build a lister without its url nor its instance should raise"""
    # ... It will raise without any of those
    with pytest.raises(ValueError, match="'url' or 'instance'"):
        GitilesLister(swh_scheduler)


def test_lister_gitiles_get_pages(requests_mock_datadir, swh_scheduler):
    """Computing the number of pages scrapped during a listing."""
    url = MAIN_INSTANCE_URL
    lister_gitiles = GitilesLister(swh_scheduler, instance=MAIN_INSTANCE)

    expected_nb_origins = 7

    repos: List[str] = list(lister_gitiles.get_pages())
    assert len(repos) == expected_nb_origins

    for listed_url in repos:
        assert listed_url.startswith(url)


@pytest.mark.parametrize(
    "url,expected_nb_origins",
    [(MAIN_INSTANCE_URL, 7), ("https://gerrit.googlesource.com", 3)],
)
def test_lister_gitiles_run(
    requests_mock_datadir, swh_scheduler, url, expected_nb_origins
):
    """Gitiles lister nominal listing case."""
    lister_gitiles = GitilesLister(swh_scheduler, url=url)

    stats = lister_gitiles.run()

    assert stats == ListerStats(pages=expected_nb_origins, origins=expected_nb_origins)

    # test page parsing
    scheduler_origins = swh_scheduler.get_listed_origins(
        lister_gitiles.lister_obj.id
    ).results
    assert len(scheduler_origins) == expected_nb_origins

    assert url.startswith("https://")

    # test listed repositories
    for listed_origin in scheduler_origins:
        assert listed_origin.visit_type == "git"
        assert listed_origin.url.startswith(url)
        assert listed_origin.url.startswith("https://")
        assert listed_origin.last_update is None

    # test user agent content
    for request in requests_mock_datadir.request_history:
        assert "User-Agent" in request.headers
        user_agent = request.headers["User-Agent"]
        assert "Software Heritage gitiles lister" in user_agent
        assert __version__ in user_agent


def test_lister_gitiles_get_pages_with_pages_and_retry(
    requests_mock_datadir, requests_mock, datadir, mocker, swh_scheduler
):
    """Rate limited page are tested back after some time so ingestion can proceed."""
    url = MAIN_INSTANCE_URL
    with open(
        os.path.join(datadir, f"https_{MAIN_INSTANCE}/,format=json"), "rb"
    ) as page:
        requests_mock.get(
            url,
            [
                {"content": None, "status_code": 429},
                {"content": None, "status_code": 429},
                {"content": page.read(), "status_code": 200},
            ],
        )

        lister_gitiles = GitilesLister(swh_scheduler, url=url)

        pages: List[str] = list(lister_gitiles.get_pages())
        assert len(pages) == 7
