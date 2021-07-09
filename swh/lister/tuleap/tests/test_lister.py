# Copyright (C) 2021 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json
from pathlib import Path
from typing import Dict, List, Tuple

import pytest
import requests

from swh.lister.tuleap.lister import RepoPage, TuleapLister
from swh.scheduler.model import ListedOrigin

TULEAP_URL = "https://tuleap.net/"
TULEAP_PROJECTS_URL = TULEAP_URL + "api/projects/"
TULEAP_REPO_1_URL = TULEAP_URL + "api/projects/685/git"  # manjaromemodoc
TULEAP_REPO_2_URL = TULEAP_URL + "api/projects/309/git"  # myaurora
TULEAP_REPO_3_URL = TULEAP_URL + "api/projects/1080/git"  # tuleap cleanup module

GIT_REPOS = (
    "https://tuleap.net/plugins/git/manjaromemodoc/manjaro-memo-documentation.git",
    "https://tuleap.net/plugins/git/myaurora/myaurora.git",
)


@pytest.fixture
def tuleap_projects(datadir) -> Tuple[str, Dict[str, str], List[str]]:
    text = Path(datadir, "https_tuleap.net", "projects").read_text()
    headers = {
        "X-PAGINATION-LIMIT-MAX": "50",
        "X-PAGINATION-LIMIT": "10",
        "X-PAGINATION-SIZE": "2",
    }
    repo_json = json.loads(text)
    projects = [p["shortname"] for p in repo_json]
    return text, headers, projects


@pytest.fixture
def tuleap_repo_1(datadir) -> Tuple[str, Dict[str, str], List[RepoPage], List[str]]:
    text = Path(datadir, "https_tuleap.net", "repo_1").read_text()
    headers = {
        "X-PAGINATION-LIMIT-MAX": "50",
        "X-PAGINATION-LIMIT": "10",
        "X-PAGINATION-SIZE": "1",
    }
    reps = json.loads(text)
    page_results = []
    for r in reps["repositories"]:
        page_results.append(
            TuleapLister.results_simplified(url=TULEAP_URL, repo_type="git", repo=r)
        )
    origin_urls = [r["uri"] for r in page_results]
    return text, headers, page_results, origin_urls


@pytest.fixture
def tuleap_repo_2(datadir) -> Tuple[str, Dict[str, str], List[RepoPage], List[str]]:
    text = Path(datadir, "https_tuleap.net", "repo_2").read_text()
    headers = {
        "X-PAGINATION-LIMIT-MAX": "50",
        "X-PAGINATION-LIMIT": "10",
        "X-PAGINATION-SIZE": "1",
    }
    reps = json.loads(text)
    page_results = []
    for r in reps["repositories"]:
        page_results.append(
            TuleapLister.results_simplified(url=TULEAP_URL, repo_type="git", repo=r)
        )
    origin_urls = [r["uri"] for r in page_results]
    return text, headers, page_results, origin_urls


@pytest.fixture
def tuleap_repo_3(datadir) -> Tuple[str, Dict[str, str], List[RepoPage], List[str]]:
    text = Path(datadir, "https_tuleap.net", "repo_3").read_text()
    headers = {
        "X-PAGINATION-LIMIT-MAX": "50",
        "X-PAGINATION-LIMIT": "10",
        "X-PAGINATION-SIZE": "0",
    }
    reps = json.loads(text)
    page_results = []
    for r in reps["repositories"]:
        page_results.append(
            TuleapLister.results_simplified(url=TULEAP_URL, repo_type="git", repo=r)
        )
    origin_urls = [r["uri"] for r in page_results]
    return text, headers, page_results, origin_urls


def check_listed_origins(lister_urls: List[str], scheduler_origins: List[ListedOrigin]):
    """Asserts that the two collections have the same origin URLs.

    Does not test last_update."""

    sorted_lister_urls = list(sorted(lister_urls))
    sorted_scheduler_origins = list(sorted(scheduler_origins))

    assert len(sorted_lister_urls) == len(sorted_scheduler_origins)

    for l_url, s_origin in zip(sorted_lister_urls, sorted_scheduler_origins):
        assert l_url == s_origin.url


def test_tuleap_full_listing(
    swh_scheduler,
    requests_mock,
    mocker,
    tuleap_projects,
    tuleap_repo_1,
    tuleap_repo_2,
    tuleap_repo_3,
):
    """Covers full listing of multiple pages, rate-limit, page size (required for test),
    checking page results and listed origins, statelessness."""

    lister = TuleapLister(
        scheduler=swh_scheduler, url=TULEAP_URL, instance="tuleap.net"
    )

    p_text, p_headers, p_projects = tuleap_projects
    r1_text, r1_headers, r1_result, r1_origin_urls = tuleap_repo_1
    r2_text, r2_headers, r2_result, r2_origin_urls = tuleap_repo_2
    r3_text, r3_headers, r3_result, r3_origin_urls = tuleap_repo_3

    requests_mock.get(TULEAP_PROJECTS_URL, text=p_text, headers=p_headers)
    requests_mock.get(TULEAP_REPO_1_URL, text=r1_text, headers=r1_headers)
    requests_mock.get(
        TULEAP_REPO_2_URL,
        [
            {"status_code": requests.codes.too_many_requests},
            {"text": r2_text, "headers": r2_headers},
        ],
    )
    requests_mock.get(TULEAP_REPO_3_URL, text=r3_text, headers=r3_headers)

    # end test setup

    stats = lister.run()

    # start test checks
    assert stats.pages == 2
    assert stats.origins == 2

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    check_listed_origins(
        r1_origin_urls + r2_origin_urls + r3_origin_urls, scheduler_origins
    )
    check_listed_origins(GIT_REPOS, scheduler_origins)

    assert lister.get_state_from_scheduler() is None


@pytest.mark.parametrize("http_code", [400, 500, 502])
def test_tuleap_list_http_error(swh_scheduler, requests_mock, http_code):
    """Test handling of some HTTP errors commonly encountered"""

    lister = TuleapLister(scheduler=swh_scheduler, url=TULEAP_URL)

    requests_mock.get(TULEAP_PROJECTS_URL, status_code=http_code)

    with pytest.raises(requests.HTTPError):
        lister.run()

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    assert len(scheduler_origins) == 0
