# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json
from pathlib import Path
from typing import List
from unittest.mock import Mock

import pytest
from requests import HTTPError

from swh.lister.gogs.lister import GogsLister
from swh.scheduler.model import ListedOrigin

TRY_GOGS_URL = "https://try.gogs.io/api/v1/"


def try_gogs_page(n: int):
    return TRY_GOGS_URL + f"repos/search?page={n}&limit=3"


@pytest.fixture
def trygogs_p1(datadir):
    text = Path(datadir, "https_try.gogs.io", "repos_page1").read_text()
    headers = {
        "Link": '<{p2}>; rel="next",<{p2}>; rel="last"'.format(p2=try_gogs_page(2))
    }
    page_result = GogsLister.results_simplified(json.loads(text))
    origin_urls = [r["clone_url"] for r in page_result]
    return text, headers, page_result, origin_urls


@pytest.fixture
def trygogs_p2(datadir):
    text = Path(datadir, "https_try.gogs.io", "repos_page2").read_text()
    headers = {
        "Link": '<{p1}>; rel="prev",<{p1}>; rel="first"'.format(p1=try_gogs_page(1))
    }
    page_result = GogsLister.results_simplified(json.loads(text))
    origin_urls = [r["clone_url"] for r in page_result]
    return text, headers, page_result, origin_urls


@pytest.fixture
def trygogs_empty_page():
    origins_urls = []
    page_result = {"data": [], "ok": True}
    headers = {
        "Link": '<{p1}>; rel="prev",<{p1}>; rel="first"'.format(p1=try_gogs_page(1))
    }
    text = json.dumps(page_result)
    return text, headers, page_result, origins_urls


def check_listed_origins(lister_urls: List[str], scheduler_origins: List[ListedOrigin]):
    """Asserts that the two collections have the same origin URLs.

    Does not test last_update."""

    sorted_lister_urls = list(sorted(lister_urls))
    sorted_scheduler_origins = list(sorted(scheduler_origins))

    assert len(sorted_lister_urls) == len(sorted_scheduler_origins)

    for l_url, s_origin in zip(sorted_lister_urls, sorted_scheduler_origins):
        assert l_url == s_origin.url


def test_gogs_full_listing(
    swh_scheduler, requests_mock, mocker, trygogs_p1, trygogs_p2, trygogs_empty_page
):
    kwargs = dict(
        url=TRY_GOGS_URL, instance="try_gogs", page_size=3, api_token="secret"
    )
    lister = GogsLister(scheduler=swh_scheduler, **kwargs)

    lister.get_origins_from_page: Mock = mocker.spy(lister, "get_origins_from_page")

    p1_text, p1_headers, p1_result, p1_origin_urls = trygogs_p1
    p2_text, p2_headers, p2_result, p2_origin_urls = trygogs_p2
    p3_text, p3_headers, _, _ = trygogs_empty_page

    requests_mock.get(try_gogs_page(1), text=p1_text, headers=p1_headers)
    requests_mock.get(try_gogs_page(2), text=p2_text, headers=p2_headers)
    requests_mock.get(try_gogs_page(3), text=p3_text, headers=p3_headers)

    stats = lister.run()

    assert stats.pages == 2
    assert stats.origins == 6

    calls = [mocker.call(p1_result), mocker.call(p2_result)]
    lister.get_origins_from_page.assert_has_calls(calls)

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    check_listed_origins(p1_origin_urls + p2_origin_urls, scheduler_origins)

    assert lister.get_state_from_scheduler() is None


def test_gogs_auth_instance(
    swh_scheduler, requests_mock, trygogs_p1, trygogs_empty_page
):
    """Covers token authentication, token from credentials,
    instance inference from URL."""

    api_token = "secret"
    instance = "try.gogs.io"
    creds = {"gogs": {instance: [{"username": "u", "password": api_token}]}}

    kwargs1 = dict(url=TRY_GOGS_URL, api_token=api_token, instance=instance)
    lister = GogsLister(scheduler=swh_scheduler, **kwargs1)

    # test API token
    assert "Authorization" in lister.session.headers
    assert lister.session.headers["Authorization"].lower() == "token %s" % api_token

    with pytest.raises(ValueError, match="No credentials or API token provided"):
        kwargs2 = dict(url=TRY_GOGS_URL, instance=instance)
        GogsLister(scheduler=swh_scheduler, **kwargs2)

    kwargs3 = dict(url=TRY_GOGS_URL, credentials=creds, instance=instance, page_size=3)
    lister = GogsLister(scheduler=swh_scheduler, **kwargs3)

    # test API token from credentials
    assert "Authorization" in lister.session.headers
    assert lister.session.headers["Authorization"].lower() == "token %s" % api_token

    # test instance inference from URL
    assert lister.instance
    assert "gogs" in lister.instance

    # setup requests mocking
    p1_text, p1_headers, _, _ = trygogs_p1
    p2_text, p2_headers, _, _ = trygogs_empty_page

    base_url = TRY_GOGS_URL + lister.REPO_LIST_PATH
    requests_mock.get(base_url, text=p1_text, headers=p1_headers)
    requests_mock.get(try_gogs_page(2), text=p2_text, headers=p2_headers)
    # now check the lister runs without error
    stats = lister.run()

    assert stats.pages == 2
    assert stats.origins == 3


@pytest.mark.parametrize("http_code", [400, 500, 502])
def test_gogs_list_http_error(swh_scheduler, requests_mock, http_code):
    """Test handling of some HTTP errors commonly encountered"""

    lister = GogsLister(scheduler=swh_scheduler, url=TRY_GOGS_URL, api_token="secret")

    base_url = TRY_GOGS_URL + lister.REPO_LIST_PATH
    requests_mock.get(base_url, status_code=http_code)

    with pytest.raises(HTTPError):
        lister.run()

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    assert len(scheduler_origins) == 0
