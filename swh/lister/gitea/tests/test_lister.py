# Copyright (C) 2017-2020 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json
from pathlib import Path
from pprint import pprint
from typing import Dict, List, Tuple

import pytest
import requests

from swh.lister.gitea.lister import GiteaLister, RepoListPage
from swh.scheduler.model import ListedOrigin

TRYGITEA_BASEURL = "https://try.gitea.io/api/v1/"
TRYGITEA_P1_URL = TRYGITEA_BASEURL + "repos/search?sort=id&order=asc&limit=3&page=1"
TRYGITEA_P2_URL = TRYGITEA_BASEURL + "repos/search?sort=id&order=asc&limit=3&page=2"


@pytest.fixture
def trygitea_p1(datadir) -> Tuple[str, Dict[str, str], RepoListPage, List[str]]:
    text = Path(datadir, "https_try.gitea.io", "repos_page1").read_text()
    headers = {
        "Link": '<{p2}>; rel="next",<{p2}>; rel="last"'.format(p2=TRYGITEA_P2_URL)
    }
    page_result = GiteaLister.results_simplified(json.loads(text))
    origin_urls = [r["clone_url"] for r in page_result]
    return text, headers, page_result, origin_urls


@pytest.fixture
def trygitea_p2(datadir) -> Tuple[str, Dict[str, str], RepoListPage, List[str]]:
    text = Path(datadir, "https_try.gitea.io", "repos_page2").read_text()
    headers = {
        "Link": '<{p1}>; rel="prev",<{p1}>; rel="first"'.format(p1=TRYGITEA_P1_URL)
    }
    page_result = GiteaLister.results_simplified(json.loads(text))
    origin_urls = [r["clone_url"] for r in page_result]
    return text, headers, page_result, origin_urls


def check_listed_origins(lister_urls: List[str], scheduler_origins: List[ListedOrigin]):
    """Asserts that the two collections have the same origin URLs.

    Does not test last_update."""

    sorted_lister_urls = list(sorted(lister_urls))
    sorted_scheduler_origins = list(sorted(scheduler_origins))

    assert len(sorted_lister_urls) == len(sorted_scheduler_origins)

    for l_url, s_origin in zip(sorted_lister_urls, sorted_scheduler_origins):
        assert l_url == s_origin.url


def test_gitea_full_listing(
    swh_scheduler, requests_mock, mocker, trygitea_p1, trygitea_p2
):
    """Covers full listing of multiple pages, instance inference from URL,
    rate-limit, token authentication, token from credentials,
    page size (required for test), checking page results and listed origins,
    statelessness."""

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

    instance = "try.gitea.io"
    api_token = "p"
    creds = {"gitea": {instance: [{"username": "u", "password": api_token}]}}
    kwargs = dict(url=TRYGITEA_BASEURL, page_size=3, credentials=creds)

    lister = GiteaLister(scheduler=swh_scheduler, **kwargs)

    assert lister.instance == instance
    assert (
        "Authorization" in lister.session.headers
        and lister.session.headers["Authorization"].lower() == "token %s" % api_token
    )

    lister.get_origins_from_page = mocker.spy(lister, "get_origins_from_page")

    # end test setup

    stats = lister.run()

    # start test checks

    assert stats.pages == 2
    assert stats.origins == 6

    # ~pprint(lister.get_origins_from_page.call_args_list)
    calls = [mocker.call(p1_result), mocker.call(p2_result)]
    lister.get_origins_from_page.assert_has_calls(calls)

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).origins

    assert lister.get_state_from_scheduler() is None
    check_listed_origins(p1_origin_urls + p2_origin_urls, scheduler_origins)


@pytest.mark.parametrize("http_code", [400, 500, 502])
def test_gitea_list_http_error(swh_scheduler, requests_mock, http_code):
    """Test handling of some HTTP errors commonly encountered"""

    requests_mock.get(TRYGITEA_P1_URL, status_code=http_code)

    lister = GiteaLister(scheduler=swh_scheduler, url=TRYGITEA_BASEURL, page_size=3)

    with pytest.raises(requests.HTTPError):
        lister.run()

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).origins
    assert len(scheduler_origins) == 0
