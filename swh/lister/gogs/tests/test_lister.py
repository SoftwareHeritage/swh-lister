# Copyright (C) 2022-2024  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json
from pathlib import Path
from typing import List
from unittest.mock import Mock
from urllib.parse import parse_qs, urlparse

import pytest
from requests import HTTPError

from swh.lister.gogs.lister import GogsLister, GogsListerPage, _parse_page_id
from swh.scheduler.model import ListedOrigin

TRY_GOGS_URL = "https://try.gogs.io/api/v1/"


def try_gogs_page(n: int):
    return TRY_GOGS_URL + GogsLister.REPO_LIST_PATH + f"?q=_&page={n}&limit=3"


P1 = try_gogs_page(1)
P2 = try_gogs_page(2)
P3 = try_gogs_page(3)
P4 = try_gogs_page(4)


@pytest.fixture
def trygogs_p1(datadir):
    text = Path(datadir, "https_try.gogs.io", "repos_page1").read_text()
    headers = {"Link": f'<{P2}>; rel="next"'}
    page_result = GogsListerPage(
        repos=GogsLister.extract_repos(json.loads(text)), next_link=P2
    )
    origin_urls = [r["clone_url"] for r in page_result.repos]
    return text, headers, page_result, origin_urls


@pytest.fixture
def trygogs_p2(datadir):
    text = Path(datadir, "https_try.gogs.io", "repos_page2").read_text()
    headers = {"Link": f'<{P3}>; rel="next",<{P1}>; rel="prev"'}
    page_result = GogsListerPage(
        repos=GogsLister.extract_repos(json.loads(text)), next_link=P3
    )
    origin_urls = [r["clone_url"] for r in page_result.repos]
    return text, headers, page_result, origin_urls


@pytest.fixture
def trygogs_p3(datadir):
    text = Path(datadir, "https_try.gogs.io", "repos_page3").read_text()
    headers = {"Link": f'<{P4}>; rel="next",<{P2}>; rel="prev"'}
    page_result = GogsListerPage(
        repos=GogsLister.extract_repos(json.loads(text)), next_link=P3
    )
    origin_urls = [r["clone_url"] for r in page_result.repos]
    return text, headers, page_result, origin_urls


@pytest.fixture
def trygogs_p4(datadir):
    text = Path(datadir, "https_try.gogs.io", "repos_page4").read_text()
    headers = {"Link": f'<{P3}>; rel="prev"'}
    page_result = GogsListerPage(
        repos=GogsLister.extract_repos(json.loads(text)), next_link=P3
    )
    origin_urls = [r["clone_url"] for r in page_result.repos]
    return text, headers, page_result, origin_urls


@pytest.fixture
def trygogs_p3_last(datadir):
    text = Path(datadir, "https_try.gogs.io", "repos_page3").read_text()
    headers = {"Link": f'<{P2}>; rel="prev",<{P1}>; rel="first"'}
    page_result = GogsListerPage(
        repos=GogsLister.extract_repos(json.loads(text)), next_link=None
    )
    origin_urls = [r["clone_url"] for r in page_result.repos]
    return text, headers, page_result, origin_urls


@pytest.fixture
def trygogs_p3_empty():
    origins_urls = []
    body = {"data": [], "ok": True}
    headers = {"Link": f'<{P2}>; rel="prev",<{P1}>; rel="first"'}
    page_result = GogsListerPage(repos=GogsLister.extract_repos(body), next_link=None)
    text = json.dumps(body)
    return text, headers, page_result, origins_urls


def check_listed_origins(lister_urls: List[str], scheduler_origins: List[ListedOrigin]):
    """Asserts that the two collections have the same origin URLs.

    Does not test last_update."""
    assert set(lister_urls) == {origin.url for origin in scheduler_origins}


def test_lister_gogs_fail_to_instantiate(swh_scheduler):
    """Build a lister without its url nor its instance should raise"""
    # while instantiating a gogs lister is fine with the url or the instance...
    assert GogsLister(swh_scheduler, url="https://try.gogs.io/api/v1") is not None
    assert GogsLister(swh_scheduler, instance="try.gogs.io") is not None

    # ... It will raise without any of those
    with pytest.raises(ValueError, match="'url' or 'instance'"):
        GogsLister(swh_scheduler)


def test_gogs_full_listing(
    swh_scheduler, requests_mock, mocker, trygogs_p1, trygogs_p2, trygogs_p3_last
):
    kwargs = dict(instance="try.gogs.io", page_size=3, api_token="secret")
    lister = GogsLister(scheduler=swh_scheduler, **kwargs)
    assert lister.url == TRY_GOGS_URL

    lister.get_origins_from_page: Mock = mocker.spy(lister, "get_origins_from_page")

    p1_text, p1_headers, p1_result, p1_origin_urls = trygogs_p1
    p2_text, p2_headers, p2_result, p2_origin_urls = trygogs_p2
    p3_text, p3_headers, p3_result, p3_origin_urls = trygogs_p3_last

    requests_mock.get(P1, text=p1_text, headers=p1_headers)
    requests_mock.get(P2, text=p2_text, headers=p2_headers)
    requests_mock.get(P3, text=p3_text, headers=p3_headers)

    stats = lister.run()

    assert stats.pages == 3
    assert stats.origins == 9

    calls = map(mocker.call, [p1_result, p2_result, p3_result])
    lister.get_origins_from_page.assert_has_calls(list(calls))

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    check_listed_origins(
        p1_origin_urls + p2_origin_urls + p3_origin_urls, scheduler_origins
    )

    assert (
        lister.get_state_from_scheduler().last_seen_next_link == P3
    )  # P3 didn't provide any next link so it remains the last_seen_next_link

    # check each query parameter has a single instance in Gogs API URLs
    for request in requests_mock.request_history:
        assert all(
            len(values) == 1
            for values in parse_qs(urlparse(request.url).query).values()
        )


def test_gogs_auth_instance(
    swh_scheduler, requests_mock, trygogs_p1, trygogs_p2, trygogs_p3_empty
):
    """Covers without authentication, token authentication, token from credentials,
    instance inference from URL."""

    api_token = "secret"
    instance = "try_gogs"

    # Test lister initialization without api_token or credentials:
    kwargs1 = dict(url=TRY_GOGS_URL, instance=instance)
    lister = GogsLister(scheduler=swh_scheduler, **kwargs1)
    assert "Authorization" not in lister.session.headers

    # Test lister initialization using api_token:
    kwargs2 = dict(url=TRY_GOGS_URL, api_token=api_token, instance=instance)
    lister = GogsLister(scheduler=swh_scheduler, **kwargs2)
    assert lister.session.headers["Authorization"].lower() == "token %s" % api_token

    # Test lister initialization with credentials and run it:
    creds = {"gogs": {instance: [{"username": "u", "password": api_token}]}}
    kwargs3 = dict(url=TRY_GOGS_URL, credentials=creds, instance=instance, page_size=3)
    lister = GogsLister(scheduler=swh_scheduler, **kwargs3)
    assert lister.session.headers["Authorization"].lower() == "token %s" % api_token
    assert lister.instance == "try_gogs"

    # setup requests mocking
    p1_text, p1_headers, _, _ = trygogs_p1
    p2_text, p2_headers, _, _ = trygogs_p2
    p3_text, p3_headers, _, _ = trygogs_p3_empty

    requests_mock.get(P1, text=p1_text, headers=p1_headers)
    requests_mock.get(P2, text=p2_text, headers=p2_headers)
    requests_mock.get(P3, text=p3_text, headers=p3_headers)

    # lister should run without any error and extract the origins
    stats = lister.run()
    assert stats.pages == 3
    assert stats.origins == 6


@pytest.mark.parametrize("http_code", [400, 500])
def test_gogs_list_http_error(
    swh_scheduler, requests_mock, http_code, trygogs_p1, trygogs_p3_last
):
    """Test handling of some HTTP errors commonly encountered"""

    lister = GogsLister(scheduler=swh_scheduler, url=TRY_GOGS_URL, api_token="secret")

    p1_text, p1_headers, _, p1_origin_urls = trygogs_p1
    p3_text, p3_headers, _, p3_origin_urls = trygogs_p3_last

    base_url = TRY_GOGS_URL + lister.REPO_LIST_PATH
    requests_mock.get(
        base_url,
        [
            {"text": p1_text, "headers": p1_headers, "status_code": 200},
            {"status_code": http_code},
            {"text": p3_text, "headers": p3_headers, "status_code": 200},
        ],
    )

    # pages with fatal repositories should be skipped (no error raised)
    # See T4423 for more details
    if http_code == 500:
        lister.run()
    else:
        with pytest.raises(HTTPError):
            lister.run()

    # Both P1 and P3 origins should be listed in case of 500 error
    # While in other cases, only P1 origins should be listed
    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    check_listed_origins(
        (p1_origin_urls + p3_origin_urls) if http_code == 500 else p1_origin_urls,
        scheduler_origins,
    )


def test_gogs_incremental_lister(
    swh_scheduler,
    requests_mock,
    mocker,
    trygogs_p1,
    trygogs_p2,
    trygogs_p3,
    trygogs_p3_last,
    trygogs_p3_empty,
    trygogs_p4,
):
    kwargs = dict(
        url=TRY_GOGS_URL, instance="try_gogs", page_size=3, api_token="secret"
    )
    lister = GogsLister(scheduler=swh_scheduler, **kwargs)

    lister.get_origins_from_page: Mock = mocker.spy(lister, "get_origins_from_page")

    # First listing attempt: P1 and P2 return 3 origins each
    # while P3 (current last page) is empty.

    p1_text, p1_headers, p1_result, p1_origin_urls = trygogs_p1
    p2_text, p2_headers, p2_result, p2_origin_urls = trygogs_p2
    p3_text, p3_headers, p3_result, p3_origin_urls = trygogs_p3_empty

    requests_mock.get(P1, text=p1_text, headers=p1_headers)
    requests_mock.get(P2, text=p2_text, headers=p2_headers)
    requests_mock.get(P3, text=p3_text, headers=p3_headers)

    attempt1_stats = lister.run()
    assert attempt1_stats.pages == 3
    assert attempt1_stats.origins == 6

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    lister_state = lister.get_state_from_scheduler()
    assert lister_state.last_seen_next_link == P3
    assert lister_state.last_seen_repo_id == p2_result.repos[-1]["id"]
    assert lister.updated

    check_listed_origins(p1_origin_urls + p2_origin_urls, scheduler_origins)

    lister.updated = False  # Reset the flag

    # Second listing attempt: P3 isn't empty anymore.
    # The lister should restart from last state and hence revisit P3.
    p3_text, p3_headers, p3_result, p3_origin_urls = trygogs_p3_last
    requests_mock.get(P3, text=p3_text, headers=p3_headers)

    lister.session.request = mocker.spy(lister.session, "request")

    attempt2_stats = lister.run()

    assert attempt2_stats.pages == 1
    assert attempt2_stats.origins == 3

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    page_id = _parse_page_id(lister_state.last_seen_next_link)
    query_params = lister.query_params
    query_params["page"] = page_id

    lister.session.request.assert_called_once_with(
        "GET", TRY_GOGS_URL + lister.REPO_LIST_PATH, params=query_params
    )

    # All the 9 origins (3 pages) should be passed on to the scheduler:
    check_listed_origins(
        p1_origin_urls + p2_origin_urls + p3_origin_urls, scheduler_origins
    )
    lister_state = lister.get_state_from_scheduler()
    assert lister_state.last_seen_next_link == P3
    assert lister_state.last_seen_repo_id == p3_result.repos[-1]["id"]
    assert lister.updated

    lister.updated = False  # Reset the flag

    # Third listing attempt: No new origins
    # The lister should revisit last seen page (P3)
    attempt3_stats = lister.run()

    assert attempt3_stats.pages == 1
    assert attempt3_stats.origins == 3

    lister_state = lister.get_state_from_scheduler()
    assert lister_state.last_seen_next_link == P3
    assert lister_state.last_seen_repo_id == p3_result.repos[-1]["id"]
    assert lister.updated is False  # No new origins so state isn't updated.

    # Fourth listing attempt: Page 4 is introduced and returns 3 new origins
    # The lister should revisit last seen page (P3) as well as P4.
    p3_text, p3_headers, p3_result, p3_origin_urls = trygogs_p3  # new P3 points to P4
    p4_text, p4_headers, p4_result, p4_origin_urls = trygogs_p4

    requests_mock.get(P3, text=p3_text, headers=p3_headers)
    requests_mock.get(P4, text=p4_text, headers=p4_headers)

    attempt4_stats = lister.run()

    assert attempt4_stats.pages == 2
    assert attempt4_stats.origins == 6

    lister_state = lister.get_state_from_scheduler()
    assert lister_state.last_seen_next_link == P4
    assert lister_state.last_seen_repo_id == p4_result.repos[-1]["id"]
    assert lister.updated

    # All the 12 origins (4 pages) should be passed on to the scheduler:
    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    check_listed_origins(
        p1_origin_urls + p2_origin_urls + p3_origin_urls + p4_origin_urls,
        scheduler_origins,
    )
