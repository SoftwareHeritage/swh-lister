# Copyright (C) 2017-2024 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import functools
import json
import logging
from pathlib import Path
from typing import Dict, List

import pytest
from requests.status_codes import codes

from swh.core.retry import WAIT_EXP_BASE
from swh.lister import USER_AGENT_TEMPLATE
from swh.lister.gitlab.lister import GitLabLister, _parse_id_after
from swh.lister.pattern import ListerStats
from swh.lister.tests.utils import assert_sleep_calls

logger = logging.getLogger(__name__)


def api_url(instance: str) -> str:
    return f"https://{instance}/api/v4"


def _match_request(request, lister_name="gitlab"):
    return request.headers.get("User-Agent") == USER_AGENT_TEMPLATE % lister_name


def test_lister_gitlab_fail_to_instantiate(swh_scheduler):
    """Build a lister without its url nor its instance should raise"""
    # while instantiating a gitlab lister is fine with the url or the instance...
    assert GitLabLister(swh_scheduler, url="https://gitlab.com/api/v4") is not None
    assert GitLabLister(swh_scheduler, instance="gitlab.fr") is not None

    # ... It will raise without any of those
    with pytest.raises(ValueError, match="'url' or 'instance'"):
        GitLabLister(swh_scheduler)


def test_lister_gitlab(datadir, swh_scheduler, requests_mock):
    """Gitlab lister supports full listing"""
    instance = "gitlab.com"
    lister = GitLabLister(swh_scheduler, instance=instance)

    assert lister.url == api_url(instance)

    response = gitlab_page_response(datadir, instance, 1)

    requests_mock.get(
        lister.page_url(),
        [{"json": response}],
        additional_matcher=_match_request,
    )

    listed_result = lister.run()
    expected_nb_origins = len(response)
    assert listed_result == ListerStats(pages=1, origins=expected_nb_origins)

    scheduler_origins = lister.scheduler.get_listed_origins(
        lister.lister_obj.id
    ).results
    assert len(scheduler_origins) == expected_nb_origins

    for listed_origin in scheduler_origins:
        assert listed_origin.visit_type == "git"
        assert listed_origin.url.startswith(f"https://{instance}")
        assert listed_origin.last_update is not None


def test_lister_gitlab_heptapod(datadir, swh_scheduler, requests_mock):
    """Heptapod lister happily lists hg, hg_git as hg and git origins"""
    name = "heptapod"
    instance = "foss.heptapod.net"
    lister = GitLabLister(
        swh_scheduler, url=api_url(instance), name=name, instance=instance
    )
    assert lister.LISTER_NAME == name

    response = gitlab_page_response(datadir, instance, 1)

    requests_mock.get(
        lister.page_url(),
        [{"json": response}],
        additional_matcher=functools.partial(_match_request, lister_name="heptapod"),
    )

    listed_result = lister.run()
    expected_nb_origins = len(response)

    for entry in response:
        assert entry["vcs_type"] in ("hg", "hg_git")

    assert listed_result == ListerStats(pages=1, origins=expected_nb_origins)

    scheduler_origins = lister.scheduler.get_listed_origins(
        lister.lister_obj.id
    ).results
    assert len(scheduler_origins) == expected_nb_origins

    for listed_origin in scheduler_origins:
        assert listed_origin.visit_type == "hg"
        assert listed_origin.url.startswith(f"https://{instance}")
        assert listed_origin.last_update is not None


def gitlab_page_response(datadir, instance: str, id_after: int) -> List[Dict]:
    """Return list of repositories (out of test dataset)"""
    datapath = Path(datadir, f"https_{instance}", f"api_response_page{id_after}.json")
    return json.loads(datapath.read_text()) if datapath.exists() else []


def test_lister_gitlab_with_pages(swh_scheduler, requests_mock, datadir):
    """Gitlab lister supports pagination"""
    instance = "gite.lirmm.fr"
    lister = GitLabLister(swh_scheduler, url=api_url(instance))

    response1 = gitlab_page_response(datadir, instance, 1)
    response2 = gitlab_page_response(datadir, instance, 2)

    requests_mock.get(
        lister.page_url(),
        [{"json": response1, "headers": {"Link": f"<{lister.page_url(2)}>; rel=next"}}],
        additional_matcher=_match_request,
    )

    requests_mock.get(
        lister.page_url(2),
        [{"json": response2}],
        additional_matcher=_match_request,
    )

    listed_result = lister.run()

    expected_nb_origins = len(response1) + len(response2)
    assert listed_result == ListerStats(pages=2, origins=expected_nb_origins)

    scheduler_origins = lister.scheduler.get_listed_origins(
        lister.lister_obj.id
    ).results
    assert len(scheduler_origins) == expected_nb_origins

    for listed_origin in scheduler_origins:
        assert listed_origin.visit_type == "git"
        assert listed_origin.url.startswith(f"https://{instance}")
        assert listed_origin.last_update is not None


def test_lister_gitlab_incremental(swh_scheduler, requests_mock, datadir):
    """Gitlab lister supports incremental visits"""
    instance = "gite.lirmm.fr"
    url = api_url(instance)
    lister = GitLabLister(swh_scheduler, url=url, instance=instance, incremental=True)

    url_page1 = lister.page_url()
    response1 = gitlab_page_response(datadir, instance, 1)
    url_page2 = lister.page_url(2)
    response2 = gitlab_page_response(datadir, instance, 2)
    url_page3 = lister.page_url(3)
    response3 = gitlab_page_response(datadir, instance, 3)

    requests_mock.get(
        url_page1,
        [{"json": response1, "headers": {"Link": f"<{url_page2}>; rel=next"}}],
        additional_matcher=_match_request,
    )
    requests_mock.get(
        url_page2,
        [{"json": response2}],
        additional_matcher=_match_request,
    )

    listed_result = lister.run()

    expected_nb_origins = len(response1) + len(response2)
    assert listed_result == ListerStats(pages=2, origins=expected_nb_origins)
    assert lister.state.last_seen_next_link == url_page2

    lister2 = GitLabLister(swh_scheduler, url=url, instance=instance, incremental=True)

    # Lister will start back at the last stop
    requests_mock.get(
        url_page2,
        [{"json": response2, "headers": {"Link": f"<{url_page3}>; rel=next"}}],
        additional_matcher=_match_request,
    )
    requests_mock.get(
        url_page3,
        [{"json": response3}],
        additional_matcher=_match_request,
    )

    listed_result2 = lister2.run()

    assert listed_result2 == ListerStats(
        pages=2, origins=len(response2) + len(response3)
    )
    assert lister2.state.last_seen_next_link == url_page3

    assert lister.lister_obj.id == lister2.lister_obj.id
    scheduler_origins = lister2.scheduler.get_listed_origins(
        lister2.lister_obj.id
    ).results

    assert len(scheduler_origins) == len(response1) + len(response2) + len(response3)

    for listed_origin in scheduler_origins:
        assert listed_origin.visit_type == "git"
        assert listed_origin.url.startswith(f"https://{instance}")
        assert listed_origin.last_update is not None


def test_lister_gitlab_rate_limit(
    swh_scheduler, requests_mock, datadir, mocker, mock_sleep
):
    """Gitlab lister supports rate-limit"""
    instance = "gite.lirmm.fr"
    url = api_url(instance)
    lister = GitLabLister(swh_scheduler, url=url, instance=instance)

    url_page1 = lister.page_url()
    response1 = gitlab_page_response(datadir, instance, 1)
    url_page2 = lister.page_url(2)
    response2 = gitlab_page_response(datadir, instance, 2)

    requests_mock.get(
        url_page1,
        [{"json": response1, "headers": {"Link": f"<{url_page2}>; rel=next"}}],
        additional_matcher=_match_request,
    )
    requests_mock.get(
        url_page2,
        [
            # rate limited twice
            {"status_code": codes.forbidden, "headers": {"RateLimit-Remaining": "0"}},
            {"status_code": codes.forbidden, "headers": {"RateLimit-Remaining": "0"}},
            # ok
            {"json": response2},
        ],
        additional_matcher=_match_request,
    )

    listed_result = lister.run()

    expected_nb_origins = len(response1) + len(response2)
    assert listed_result == ListerStats(pages=2, origins=expected_nb_origins)

    assert_sleep_calls(mocker, mock_sleep, [1, WAIT_EXP_BASE])


@pytest.mark.parametrize("status_code", [502, 503, 520])
def test_lister_gitlab_http_errors(
    swh_scheduler, requests_mock, datadir, mocker, status_code, mock_sleep
):
    """Gitlab lister should retry requests when encountering HTTP 50x errors"""
    instance = "gite.lirmm.fr"
    url = api_url(instance)
    lister = GitLabLister(swh_scheduler, url=url, instance=instance)

    url_page1 = lister.page_url()
    response1 = gitlab_page_response(datadir, instance, 1)
    url_page2 = lister.page_url(2)
    response2 = gitlab_page_response(datadir, instance, 2)

    requests_mock.get(
        url_page1,
        [{"json": response1, "headers": {"Link": f"<{url_page2}>; rel=next"}}],
        additional_matcher=_match_request,
    )
    requests_mock.get(
        url_page2,
        [
            # first request ends up with error
            {"status_code": status_code},
            # second request is ok
            {"json": response2},
        ],
        additional_matcher=_match_request,
    )

    listed_result = lister.run()

    expected_nb_origins = len(response1) + len(response2)
    assert listed_result == ListerStats(pages=2, origins=expected_nb_origins)

    assert_sleep_calls(mocker, mock_sleep, [1])


def test_lister_gitlab_http_error_500(swh_scheduler, requests_mock, datadir):
    """Gitlab lister should skip buggy URL and move to next page."""
    instance = "gite.lirmm.fr"
    url = api_url(instance)
    lister = GitLabLister(swh_scheduler, url=url, instance=instance)

    url_page1 = lister.page_url()
    response1 = gitlab_page_response(datadir, instance, 1)
    url_page2 = lister.page_url(lister.per_page)
    url_page3 = lister.page_url(2 * lister.per_page)
    response3 = gitlab_page_response(datadir, instance, 3)

    requests_mock.get(
        url_page1,
        [{"json": response1, "headers": {"Link": f"<{url_page2}>; rel=next"}}],
        additional_matcher=_match_request,
    )
    requests_mock.get(
        url_page2,
        [
            {"status_code": 500},
        ],
        additional_matcher=_match_request,
    )

    requests_mock.get(
        url_page3,
        [{"json": response3}],
        additional_matcher=_match_request,
    )

    listed_result = lister.run()

    expected_nb_origins = len(response1) + len(response3)
    assert listed_result == ListerStats(pages=2, origins=expected_nb_origins)


def test_lister_gitlab_credentials(swh_scheduler):
    """Gitlab lister supports credentials configuration"""
    instance = "gitlab"
    credentials = {
        "gitlab": {instance: [{"username": "user", "password": "api-token"}]}
    }
    url = api_url(instance)
    lister = GitLabLister(
        scheduler=swh_scheduler, url=url, instance=instance, credentials=credentials
    )
    assert lister.session.headers["Authorization"] == "Bearer api-token"


@pytest.mark.parametrize(
    "url",
    [
        api_url("gitlab").rstrip("/"),
        api_url("gitlab"),
    ],
)
def test_lister_gitlab_url_computation(url, swh_scheduler):
    lister = GitLabLister(scheduler=swh_scheduler, url=url)
    assert not lister.url.endswith("/")

    page_url = lister.page_url()
    # ensure the generated url contains the separated /
    assert page_url.startswith(f"{lister.url}/projects")


@pytest.mark.parametrize(
    "url,expected_result",
    [
        (None, None),
        ("http://dummy/?query=1", None),
        ("http://dummy/?foo=bar&id_after=1&some=result", 1),
        ("http://dummy/?foo=bar&id_after=&some=result", None),
    ],
)
def test__parse_id_after(url, expected_result):
    assert _parse_id_after(url) == expected_result


def test_lister_gitlab_ignored_project_prefixes(datadir, swh_scheduler, requests_mock):
    """Gitlab lister supports listing with ignored project prefixes"""
    instance = "gitlab.com"
    lister = GitLabLister(
        swh_scheduler,
        url=api_url(instance),
        instance=instance,
        ignored_project_prefixes=["jonan/"],
    )

    response = gitlab_page_response(datadir, instance, 1)

    requests_mock.get(
        lister.page_url(),
        [{"json": response}],
        additional_matcher=_match_request,
    )

    listed_result = lister.run()
    # 2 origins start with jonan/
    expected_nb_origins = len(response) - 2
    assert listed_result == ListerStats(pages=1, origins=expected_nb_origins)

    scheduler_origins = lister.scheduler.get_listed_origins(
        lister.lister_obj.id
    ).results
    assert len(scheduler_origins) == expected_nb_origins

    for listed_origin in scheduler_origins:
        assert listed_origin.visit_type == "git"
        assert listed_origin.url.startswith(f"https://{instance}")
        assert not listed_origin.url.startswith(f"https://{instance}/jonan/")
        assert listed_origin.last_update is not None
