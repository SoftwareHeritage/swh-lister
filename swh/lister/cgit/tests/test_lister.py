# Copyright (C) 2019-2024 The Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from datetime import datetime, timedelta, timezone
import os
from typing import List

import pytest

from swh.core.pytest_plugin import requests_mock_datadir_factory
from swh.lister import __version__
from swh.lister.cgit.lister import CGitLister, _parse_last_updated_date
from swh.lister.pattern import ListerStats


def test_lister_cgit_get_pages_one_page(requests_mock_datadir, swh_scheduler):
    url = "https://git.savannah.gnu.org/cgit/"
    lister_cgit = CGitLister(swh_scheduler, url=url)

    repos: List[List[str]] = list(lister_cgit.get_pages())
    flattened_repos = sum(repos, [])
    assert len(flattened_repos) == 977

    assert flattened_repos[0]["url"] == "https://git.savannah.gnu.org/cgit/elisp-es.git"
    # note the url below is NOT a subpath of /cgit/
    assert (
        flattened_repos[-1]["url"] == "https://git.savannah.gnu.org/path/to/yetris.git"
    )  # noqa
    # note the url below is NOT on the same server
    assert flattened_repos[-2]["url"] == "http://example.org/cgit/xstarcastle.git"


def test_lister_cgit_get_pages_with_pages(requests_mock_datadir, swh_scheduler):
    url = "https://git.tizen/cgit/"
    lister_cgit = CGitLister(swh_scheduler, url=url)

    repos: List[List[str]] = list(lister_cgit.get_pages())
    flattened_repos = sum(repos, [])
    # we should have 16 repos (listed on 3 pages)
    assert len(repos) == 3
    assert len(flattened_repos) == 16


def test_lister_cgit_run_with_page(requests_mock_datadir, swh_scheduler):
    """cgit lister supports pagination"""

    url = "https://git.tizen/cgit/"
    lister_cgit = CGitLister(swh_scheduler, url=url)

    stats = lister_cgit.run()

    expected_nb_origins = 16
    assert stats == ListerStats(pages=3, origins=expected_nb_origins)

    # test page parsing
    scheduler_origins = swh_scheduler.get_listed_origins(
        lister_cgit.lister_obj.id
    ).results
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
        assert "Software Heritage cgit lister" in user_agent
        assert __version__ in user_agent


def test_lister_cgit_run_populates_last_update(requests_mock_datadir, swh_scheduler):
    """cgit lister returns last updated date"""

    url = "https://git.tizen/cgit"

    urls_without_date = [
        f"https://git.tizen.org/cgit/{suffix_url}"
        for suffix_url in [
            "All-Projects",
            "All-Users",
            "Lock-Projects",
        ]
    ]

    lister_cgit = CGitLister(swh_scheduler, url=url)

    stats = lister_cgit.run()

    expected_nb_origins = 16
    assert stats == ListerStats(pages=3, origins=expected_nb_origins)

    # test page parsing
    scheduler_origins = swh_scheduler.get_listed_origins(
        lister_cgit.lister_obj.id
    ).results
    assert len(scheduler_origins) == expected_nb_origins

    # test listed repositories
    for listed_origin in scheduler_origins:
        if listed_origin.url in urls_without_date:
            assert listed_origin.last_update is None
        else:
            assert listed_origin.last_update is not None


@pytest.mark.parametrize(
    "date_str,expected_date",
    [
        ({}, None),
        ("unexpected date", None),
        ("2020-0140-10 10:10:10 (GMT)", None),
        (
            "2020-01-10 10:10:10 (GMT)",
            datetime(
                year=2020,
                month=1,
                day=10,
                hour=10,
                minute=10,
                second=10,
                tzinfo=timezone.utc,
            ),
        ),
        (
            "2019-08-04 05:10:41 +0100",
            datetime(
                year=2019,
                month=8,
                day=4,
                hour=5,
                minute=10,
                second=41,
                tzinfo=timezone(timedelta(hours=1)),
            ),
        ),
    ],
)
def test_lister_cgit_date_parsing(date_str, expected_date):
    """test cgit lister date parsing"""

    repository = {"url": "url", "last_updated_date": date_str}

    assert _parse_last_updated_date(repository) == expected_date


requests_mock_datadir_missing_url = requests_mock_datadir_factory(
    ignore_urls=[
        "https://git.tizen/cgit/adaptation/ap_samsung/audio-hal-e4x12",
    ]
)


def test_lister_cgit_instantiate(swh_scheduler):
    """Build a lister with either an url or an instance is fine"""
    url = "https://source.codeaurora.org"
    lister = CGitLister(swh_scheduler, url=url)
    assert lister is not None
    assert lister.url == url

    assert CGitLister(swh_scheduler, instance="source.codeaurora.org") is not None
    assert lister is not None
    assert lister.url == url


def test_lister_cgit_fail_to_instantiate(swh_scheduler):
    """Build a lister without its url nor its instance should raise"""
    # ... It will raise without any of those
    with pytest.raises(ValueError, match="'url' or 'instance'"):
        CGitLister(swh_scheduler)


def test_lister_cgit_get_origin_from_repo_failing(
    requests_mock_datadir_missing_url, swh_scheduler
):
    url = "https://git.tizen/cgit/"
    lister_cgit = CGitLister(swh_scheduler, url=url)

    stats = lister_cgit.run()

    expected_nb_origins = 15
    assert stats == ListerStats(pages=3, origins=expected_nb_origins)


@pytest.mark.parametrize(
    "credentials, expected_credentials",
    [
        (None, []),
        ({"key": "value"}, []),
        (
            {"cgit": {"tizen": [{"username": "user", "password": "pass"}]}},
            [{"username": "user", "password": "pass"}],
        ),
    ],
)
def test_lister_cgit_instantiation_with_credentials(
    credentials, expected_credentials, swh_scheduler
):
    url = "https://git.tizen/cgit/"
    lister = CGitLister(
        swh_scheduler, url=url, instance="tizen", credentials=credentials
    )

    # Credentials are allowed in constructor
    assert lister.credentials == expected_credentials


def test_lister_cgit_from_configfile(swh_scheduler_config, mocker):
    load_from_envvar = mocker.patch("swh.lister.pattern.load_from_envvar")
    load_from_envvar.return_value = {
        "scheduler": {"cls": "local", **swh_scheduler_config},
        "url": "https://git.tizen/cgit/",
        "instance": "tizen",
        "credentials": {},
    }
    lister = CGitLister.from_configfile()
    assert lister.scheduler is not None
    assert lister.credentials is not None


@pytest.mark.parametrize(
    "url,base_git_url,expected_nb_origins",
    [
        ("https://git.eclipse.org/c", "https://eclipse.org/r", 5),
        ("https://git.baserock.org/cgit/", "https://git.baserock.org/git/", 3),
        ("https://jff.email/cgit/", "git://jff.email/opt/git/", 6),
    ],
)
def test_lister_cgit_with_base_git_url(
    url, base_git_url, expected_nb_origins, requests_mock_datadir, swh_scheduler
):
    """With base git url provided, listed urls should be the computed origin urls"""
    lister_cgit = CGitLister(
        swh_scheduler,
        url=url,
        base_git_url=base_git_url,
    )

    stats = lister_cgit.run()

    assert stats == ListerStats(pages=1, origins=expected_nb_origins)

    # test page parsing
    scheduler_origins = swh_scheduler.get_listed_origins(
        lister_cgit.lister_obj.id
    ).results
    assert len(scheduler_origins) == expected_nb_origins

    # test listed repositories
    for listed_origin in scheduler_origins:
        assert listed_origin.visit_type == "git"
        assert listed_origin.url.startswith(base_git_url)
        assert (
            listed_origin.url.startswith(url) is False
        ), f"url should be mapped to {base_git_url}"


def test_lister_cgit_get_pages_with_pages_and_retry(
    requests_mock_datadir, requests_mock, datadir, mocker, swh_scheduler
):
    url = "https://git.tizen/cgit/"

    with open(os.path.join(datadir, "https_git.tizen/cgit,ofs=50"), "rb") as page:
        requests_mock.get(
            f"{url}?ofs=50",
            [
                {"content": None, "status_code": 429},
                {"content": None, "status_code": 429},
                {"content": page.read(), "status_code": 200},
            ],
        )

        lister_cgit = CGitLister(swh_scheduler, url=url)

        repos: List[List[str]] = list(lister_cgit.get_pages())
        flattened_repos = sum(repos, [])
        # we should have 16 repos (listed on 3 pages)
        assert len(repos) == 3
        assert len(flattened_repos) == 16


def test_lister_cgit_summary_not_default(requests_mock_datadir, swh_scheduler):
    """cgit lister returns git url when the default repository tab is not the summary"""

    url = "https://git.acdw.net/cgit"

    lister_cgit = CGitLister(swh_scheduler, url=url)

    stats = lister_cgit.run()

    expected_nb_origins = 1
    assert stats == ListerStats(pages=1, origins=expected_nb_origins)
