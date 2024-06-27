# Copyright (C) 2023-2024 The Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os
from typing import List

import pytest

from swh.lister import __version__
from swh.lister.gitweb.lister import (
    GitwebLister,
    parse_last_update,
    try_to_determine_git_repository,
)
from swh.lister.pattern import ListerStats

MAIN_INSTANCE = "git.distorted.org.uk"
MAIN_INSTANCE_URL = f"https://{MAIN_INSTANCE}/~mdw"


def test_lister_gitweb_instantiate(swh_scheduler):
    """Build a lister with either an url or an instance is supported."""
    url = MAIN_INSTANCE_URL
    lister = GitwebLister(swh_scheduler, url=url)
    assert lister is not None
    assert lister.url == url

    assert GitwebLister(swh_scheduler, instance=MAIN_INSTANCE) is not None
    assert lister is not None
    assert lister.url == url


def test_lister_gitweb_fail_to_instantiate(swh_scheduler):
    """Build a lister without its url nor its instance should raise"""
    # ... It will raise without any of those
    with pytest.raises(ValueError, match="'url' or 'instance'"):
        GitwebLister(swh_scheduler)


def test_lister_gitweb_get_pages(requests_mock_datadir, swh_scheduler):
    """Computing the number of pages scrapped during a listing."""
    url = MAIN_INSTANCE_URL
    lister_gitweb = GitwebLister(swh_scheduler, url=url)

    expected_nb_origins = 7

    repos: List[List[str]] = list(lister_gitweb.get_pages())
    flattened_repos = sum(repos, [])
    assert len(flattened_repos) == expected_nb_origins

    for listed_url in flattened_repos:
        assert listed_url["url"].startswith(url)


def test_lister_gitweb_run(requests_mock_datadir, swh_scheduler):
    """Gitweb lister nominal listing case."""

    url = MAIN_INSTANCE_URL
    lister_gitweb = GitwebLister(swh_scheduler, url=url)

    stats = lister_gitweb.run()

    expected_nb_origins = 7  # main page will get filtered out
    assert stats == ListerStats(pages=1, origins=expected_nb_origins)

    # test page parsing
    scheduler_origins = swh_scheduler.get_listed_origins(
        lister_gitweb.lister_obj.id
    ).results
    assert len(scheduler_origins) == expected_nb_origins

    assert url.startswith("https://")

    # test listed repositories
    for listed_origin in scheduler_origins:
        assert listed_origin.visit_type == "git"
        assert listed_origin.url.startswith(url)
        assert listed_origin.url.startswith("https://")
        assert listed_origin.last_update is not None
        assert "," not in listed_origin.url

    # test user agent content
    for request in requests_mock_datadir.request_history:
        assert "User-Agent" in request.headers
        user_agent = request.headers["User-Agent"]
        assert "Software Heritage gitweb lister" in user_agent
        assert __version__ in user_agent


def test_lister_gitweb_get_pages_with_pages_and_retry(
    requests_mock_datadir, requests_mock, datadir, mocker, swh_scheduler
):
    """Rate limited page are tested back after some time so ingestion can proceed."""
    url = MAIN_INSTANCE_URL
    with open(os.path.join(datadir, f"https_{MAIN_INSTANCE}/~mdw"), "rb") as page:
        requests_mock.get(
            url,
            [
                {"content": None, "status_code": 429},
                {"content": None, "status_code": 429},
                {"content": page.read(), "status_code": 200},
            ],
        )

        lister_gitweb = GitwebLister(swh_scheduler, url=url)

        pages: List[List[str]] = list(lister_gitweb.get_pages())
        flattened_repos = sum(pages, [])
        assert len(pages) == 1
        assert len(flattened_repos) == 7


def test_lister_gitweb_get_origin_from_repo_failing(
    swh_scheduler, requests_mock_datadir
):
    """Instances whose summary does not return anything are filtered out."""
    # This instance has some more origins which no longer returns their summary
    lister_gitweb = GitwebLister(swh_scheduler, url=f"https://{MAIN_INSTANCE}/foobar")

    stats = lister_gitweb.run()

    # so they are filtered out, only the 7 we know are thus listed
    expected_nb_origins = 7
    assert stats == ListerStats(pages=1, origins=expected_nb_origins)


@pytest.mark.parametrize(
    "url,base_git_url,expected_repo",
    [
        (
            "https://git.shadowcat.co.uk?p=urisagit/gitosis-admin.git",
            None,
            "git://git.shadowcat.co.uk/urisagit/gitosis-admin.git",
        ),
        (
            "https://git.shadowcat.co.uk?p=File-Slurp.git;a=summary",
            None,
            "git://git.shadowcat.co.uk/File-Slurp.git",
        ),
        (
            "https://git.example.org?p=baaaa;a=summary",
            None,
            "git://git.example.org/baaaa",
        ),
        (
            "https://domain.org/foobar",
            None,
            None,
        ),
        (
            "https://gitweb.example.org?p=project.git;a=summary",
            "https://example.org",
            "https://example.org/project.git",
        ),
        (
            "https://example.org?p=project.git;a=summary",
            "https://example.org/git/",
            "https://example.org/git/project.git",
        ),
    ],
)
def test_try_to_determine_git_repository(url, base_git_url, expected_repo):
    assert try_to_determine_git_repository(url, base_git_url) == expected_repo


def test_parse_last_update():
    assert parse_last_update(None) is None
    assert parse_last_update("No commits") is None

    date = parse_last_update("6 months ago")
    assert date is not None
    assert date.tzinfo is not None
