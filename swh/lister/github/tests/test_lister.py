# Copyright (C) 2020-2022 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import datetime
import logging
from typing import Any, Dict, List

import pytest

from swh.core.github.pytest_plugin import github_response_callback
from swh.lister.github.lister import GitHubLister
from swh.lister.pattern import CredentialsType, ListerStats
from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import Lister

NUM_PAGES = 10
ORIGIN_COUNT = GitHubLister.PAGE_SIZE * NUM_PAGES


def response_callback(request, context):
    return github_response_callback(request, context, remaining_requests=1000)


@pytest.fixture()
def requests_mocker(requests_mock):
    requests_mock.get(GitHubLister.API_URL, json=response_callback)


def get_lister_data(swh_scheduler: SchedulerInterface) -> Lister:
    """Retrieve the data for the GitHub Lister"""
    return swh_scheduler.get_or_create_lister(name="github", instance_name="github")


def set_lister_state(swh_scheduler: SchedulerInterface, state: Dict[str, Any]) -> None:
    """Set the state of the lister in database"""
    lister = swh_scheduler.get_or_create_lister(name="github", instance_name="github")
    lister.current_state = state
    swh_scheduler.update_lister(lister)


def check_origin_4321(swh_scheduler: SchedulerInterface, lister: Lister) -> None:
    """Check that origin 4321 exists and has the proper last_update timestamp"""
    origin_4321_req = swh_scheduler.get_listed_origins(
        url="https://github.com/origin/4321"
    )
    assert len(origin_4321_req.results) == 1
    origin_4321 = origin_4321_req.results[0]
    assert origin_4321.lister_id == lister.id
    assert origin_4321.visit_type == "git"
    assert origin_4321.last_update == datetime.datetime(
        2018, 11, 8, 13, 16, 24, tzinfo=datetime.timezone.utc
    )
    assert origin_4321.is_fork is not None


def check_origin_5555(swh_scheduler: SchedulerInterface, lister: Lister) -> None:
    """Check that origin 5555 exists and has no last_update timestamp"""
    origin_5555_req = swh_scheduler.get_listed_origins(
        url="https://github.com/origin/5555"
    )
    assert len(origin_5555_req.results) == 1
    origin_5555 = origin_5555_req.results[0]
    assert origin_5555.lister_id == lister.id
    assert origin_5555.visit_type == "git"
    assert origin_5555.last_update is None


def test_from_empty_state(swh_scheduler, caplog, requests_mocker) -> None:
    caplog.set_level(logging.DEBUG, "swh.lister.github.lister")

    # Run the lister in incremental mode
    lister = GitHubLister(scheduler=swh_scheduler)
    res = lister.run()

    assert res == ListerStats(pages=NUM_PAGES, origins=ORIGIN_COUNT)

    listed_origins = swh_scheduler.get_listed_origins(limit=ORIGIN_COUNT + 1)
    assert len(listed_origins.results) == ORIGIN_COUNT
    assert listed_origins.next_page_token is None

    lister_data = get_lister_data(swh_scheduler)
    assert lister_data.current_state == {"last_seen_id": ORIGIN_COUNT}

    check_origin_4321(swh_scheduler, lister_data)
    check_origin_5555(swh_scheduler, lister_data)


def test_incremental(swh_scheduler, caplog, requests_mocker) -> None:
    caplog.set_level(logging.DEBUG, "swh.lister.github.lister")

    # Number of origins to skip
    skip_origins = 2000
    expected_origins = ORIGIN_COUNT - skip_origins

    # Bump the last_seen_id in the scheduler backend
    set_lister_state(swh_scheduler, {"last_seen_id": skip_origins})

    # Run the lister in incremental mode
    lister = GitHubLister(scheduler=swh_scheduler)
    res = lister.run()

    # add 1 page to the number of full_pages if partial_page_len is not 0
    full_pages, partial_page_len = divmod(expected_origins, GitHubLister.PAGE_SIZE)
    expected_pages = full_pages + bool(partial_page_len)

    assert res == ListerStats(pages=expected_pages, origins=expected_origins)

    listed_origins = swh_scheduler.get_listed_origins(limit=expected_origins + 1)
    assert len(listed_origins.results) == expected_origins
    assert listed_origins.next_page_token is None

    lister_data = get_lister_data(swh_scheduler)
    assert lister_data.current_state == {"last_seen_id": ORIGIN_COUNT}

    check_origin_4321(swh_scheduler, lister_data)
    check_origin_5555(swh_scheduler, lister_data)


def test_relister(swh_scheduler, caplog, requests_mocker) -> None:
    caplog.set_level(logging.DEBUG, "swh.lister.github.lister")

    # Only set this state as a canary: in the currently tested mode, the lister
    # should not be touching it.
    set_lister_state(swh_scheduler, {"last_seen_id": 123})

    # Use "relisting" mode to list origins between id 10 and 1011
    lister = GitHubLister(scheduler=swh_scheduler, first_id=10, last_id=1011)
    res = lister.run()

    # Make sure we got two full pages of results
    assert res == ListerStats(pages=2, origins=2000)

    # Check that the relisting mode hasn't touched the stored state.
    lister_data = get_lister_data(swh_scheduler)
    assert lister_data.current_state == {"last_seen_id": 123}


def test_anonymous_ratelimit(
    swh_scheduler, caplog, github_requests_ratelimited
) -> None:
    caplog.set_level(logging.DEBUG, "swh.core.github.utils")

    lister = GitHubLister(scheduler=swh_scheduler)
    assert lister.github_session is not None and lister.github_session.anonymous
    assert "using anonymous mode" in caplog.records[-1].message
    caplog.clear()

    res = lister.run()
    assert res == ListerStats(pages=0, origins=0)

    last_log = caplog.records[-1]
    assert last_log.levelname == "WARNING"
    assert "No X-Ratelimit-Reset value found in responses" in last_log.message


@pytest.fixture
def lister_credentials(github_credentials: List[Dict[str, str]]) -> CredentialsType:
    """Return the credentials formatted for use by the lister"""
    return {"github": {"github": github_credentials}}


def test_authenticated_credentials(
    swh_scheduler, caplog, github_credentials, lister_credentials, all_tokens
):
    """Test credentials management when the lister is authenticated"""
    caplog.set_level(logging.DEBUG, "swh.lister.github.lister")

    lister = GitHubLister(scheduler=swh_scheduler, credentials=lister_credentials)
    assert lister.github_session.token_index == 0
    assert sorted(lister.credentials, key=lambda t: t["username"]) == github_credentials
    assert lister.github_session.session.headers["Authorization"] in [
        "token %s" % t for t in all_tokens
    ]


@pytest.mark.parametrize(
    "num_ratelimit", [1]
)  # return a single rate-limit response, then continue
def test_ratelimit_once_recovery(
    swh_scheduler,
    caplog,
    github_requests_ratelimited,
    num_ratelimit,
    monkeypatch_sleep_calls,
    lister_credentials,
):
    """Check that the lister recovers from hitting the rate-limit once"""
    caplog.set_level(logging.DEBUG, "swh.core.github.utils")

    lister = GitHubLister(scheduler=swh_scheduler, credentials=lister_credentials)

    res = lister.run()
    # check that we used all the pages
    assert res == ListerStats(pages=NUM_PAGES, origins=ORIGIN_COUNT)

    token_users = []
    for record in caplog.records:
        if "Using authentication token" in record.message:
            token_users.append(record.args[0])

    # check that we used one more token than we saw rate limited requests
    assert len(token_users) == 1 + num_ratelimit

    # check that we slept for one second between our token uses
    assert monkeypatch_sleep_calls == [1]


@pytest.mark.parametrize(
    # Do 5 successful requests, return 6 ratelimits (to exhaust the credentials) with a
    # set value for X-Ratelimit-Reset, then resume listing successfully.
    "num_before_ratelimit, num_ratelimit, ratelimit_reset",
    [(5, 6, 123456)],
)
def test_ratelimit_reset_sleep(
    swh_scheduler,
    caplog,
    github_requests_ratelimited,
    monkeypatch_sleep_calls,
    github_credentials,
    lister_credentials,
    num_before_ratelimit,
    num_ratelimit,
    ratelimit_reset,
):
    """Check that the lister properly handles rate-limiting when providing it with
    authentication tokens"""
    caplog.set_level(logging.DEBUG, "swh.core.github.utils")

    lister = GitHubLister(scheduler=swh_scheduler, credentials=lister_credentials)

    res = lister.run()
    assert res == ListerStats(pages=NUM_PAGES, origins=ORIGIN_COUNT)

    # We sleep 1 second every time we change credentials, then we sleep until
    # ratelimit_reset + 1
    expected_sleep_calls = len(github_credentials) * [1] + [ratelimit_reset + 1]
    assert monkeypatch_sleep_calls == expected_sleep_calls

    found_exhaustion_message = False
    for record in caplog.records:
        if record.levelname == "INFO":
            if "Rate limits exhausted for all tokens" in record.message:
                found_exhaustion_message = True
                break

    assert found_exhaustion_message
