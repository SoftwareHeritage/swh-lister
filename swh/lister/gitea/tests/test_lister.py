# Copyright (C) 2017-2020 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json
from pathlib import Path
from typing import Dict, List, Tuple

import pytest
import requests
from requests import HTTPError

from swh.lister.gitea.lister import GiteaLister
from swh.lister.gogs.lister import GogsListerPage
from swh.scheduler.model import ListedOrigin

TRYGITEA_URL = "https://try.gitea.io/api/v1/"
TRYGITEA_P1_URL = TRYGITEA_URL + "repos/search?limit=3&page=1"
TRYGITEA_P2_URL = TRYGITEA_URL + "repos/search?limit=3&page=2"


@pytest.fixture
def trygitea_p1(datadir) -> Tuple[str, Dict[str, str], GogsListerPage, List[str]]:
    text = Path(datadir, "https_try.gitea.io", "repos_page1").read_text()
    headers = {
        "Link": '<{p2}>; rel="next",<{p2}>; rel="last"'.format(p2=TRYGITEA_P2_URL)
    }
    page_data = json.loads(text)
    page_result = GogsListerPage(
        repos=GiteaLister.extract_repos(page_data), next_link=TRYGITEA_P2_URL
    )
    origin_urls = [r["clone_url"] for r in page_data["data"]]
    return text, headers, page_result, origin_urls


@pytest.fixture
def trygitea_p2(datadir) -> Tuple[str, Dict[str, str], GogsListerPage, List[str]]:
    text = Path(datadir, "https_try.gitea.io", "repos_page2").read_text()
    headers = {
        "Link": '<{p1}>; rel="prev",<{p1}>; rel="first"'.format(p1=TRYGITEA_P1_URL)
    }
    page_data = json.loads(text)
    page_result = GogsListerPage(
        repos=GiteaLister.extract_repos(page_data), next_link=None
    )
    origin_urls = [r["clone_url"] for r in page_data["data"]]
    return text, headers, page_result, origin_urls


def check_listed_origins(lister_urls: List[str], scheduler_origins: List[ListedOrigin]):
    """Asserts that the two collections have the same origin URLs.

    Does not test last_update."""
    assert set(lister_urls) == {origin.url for origin in scheduler_origins}


def test_gitea_full_listing(
    swh_scheduler, requests_mock, mocker, trygitea_p1, trygitea_p2
):
    """Covers full listing of multiple pages, rate-limit, page size (required for test),
    checking page results and listed origins, statelessness."""

    kwargs = dict(url=TRYGITEA_URL, instance="try_gitea", page_size=3)
    lister = GiteaLister(scheduler=swh_scheduler, **kwargs)

    lister.get_origins_from_page = mocker.spy(lister, "get_origins_from_page")

    p1_text, p1_headers, p1_result, p1_origin_urls = trygitea_p1
    p2_text, p2_headers, p2_result, p2_origin_urls = trygitea_p2

    requests_mock.get(TRYGITEA_P1_URL, text=p1_text, headers=p1_headers)
    requests_mock.get(
        TRYGITEA_P2_URL,
        [
            {"status_code": requests.codes.too_many_requests},
            {"text": p2_text, "headers": p2_headers},
        ],
    )

    # end test setup

    stats = lister.run()

    # start test checks

    assert stats.pages == 2
    assert stats.origins == 6

    calls = [mocker.call(p1_result), mocker.call(p2_result)]
    lister.get_origins_from_page.assert_has_calls(calls)

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    check_listed_origins(p1_origin_urls + p2_origin_urls, scheduler_origins)

    lister_state = lister.get_state_from_scheduler()
    assert lister_state.last_seen_next_link == TRYGITEA_P2_URL
    assert lister_state.last_seen_repo_id == p2_result.repos[-1]["id"]


def test_gitea_auth_instance(swh_scheduler, requests_mock, trygitea_p1):
    """Covers token authentication, token from credentials,
    instance inference from URL."""

    api_token = "teapot"
    instance = "try.gitea.io"
    creds = {"gitea": {instance: [{"username": "u", "password": api_token}]}}

    kwargs1 = dict(url=TRYGITEA_URL, api_token=api_token)
    lister = GiteaLister(scheduler=swh_scheduler, **kwargs1)

    # test API token
    assert "Authorization" in lister.session.headers
    assert lister.session.headers["Authorization"].lower() == "token %s" % api_token

    kwargs2 = dict(url=TRYGITEA_URL, credentials=creds)
    lister = GiteaLister(scheduler=swh_scheduler, **kwargs2)

    # test API token from credentials
    assert "Authorization" in lister.session.headers
    assert lister.session.headers["Authorization"].lower() == "token %s" % api_token

    # test instance inference from URL
    assert lister.instance
    assert "gitea" in lister.instance  # infer something related to that

    # setup requests mocking
    p1_text, p1_headers, _, _ = trygitea_p1
    p1_headers["Link"] = p1_headers["Link"].replace("next", "")  # only 1 page

    base_url = TRYGITEA_URL + lister.REPO_LIST_PATH
    requests_mock.get(base_url, text=p1_text, headers=p1_headers)

    # now check the lister runs without error
    stats = lister.run()

    assert stats.pages == 1


@pytest.mark.parametrize("http_code", [400, 500])
def test_gitea_list_http_error(
    swh_scheduler, requests_mock, http_code, trygitea_p1, trygitea_p2
):
    """Test handling of some HTTP errors commonly encountered"""

    lister = GiteaLister(scheduler=swh_scheduler, url=TRYGITEA_URL, page_size=3)

    p1_text, p1_headers, _, p1_origin_urls = trygitea_p1
    p3_text, p3_headers, _, p3_origin_urls = trygitea_p2

    base_url = TRYGITEA_URL + lister.REPO_LIST_PATH
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
