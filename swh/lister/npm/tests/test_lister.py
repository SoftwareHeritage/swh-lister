# Copyright (C) 2018-2025 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json
from pathlib import Path

import pytest
from requests.exceptions import HTTPError

from swh.lister import USER_AGENT_TEMPLATE
from swh.lister.npm.lister import NpmLister, NpmListerState


@pytest.fixture
def npm_changes_page1(datadir):
    return json.loads(Path(datadir, "npm_changes_page1.json").read_text())


@pytest.fixture
def npm_changes_page2(datadir):
    return json.loads(Path(datadir, "npm_changes_page2.json").read_text())


def _match_request(request):
    return (
        request.headers.get("User-Agent") == USER_AGENT_TEMPLATE % NpmLister.LISTER_NAME
    )


def test_npm_lister_full(
    swh_scheduler,
    requests_mock,
    mocker,
    npm_changes_page1,
    npm_changes_page2,
):
    """Simulate a full listing of four npm packages in two pages"""
    page_size = 2
    lister = NpmLister(scheduler=swh_scheduler, page_size=page_size, incremental=False)

    requests_mock.get(
        lister.NPM_API_CHANGES_URL,
        [
            {"json": npm_changes_page1},
            {"json": npm_changes_page2},
            {"json": {"results": []}},
        ],
        additional_matcher=_match_request,
    )

    spy_request = mocker.spy(lister.session, "request")

    stats = lister.run()
    assert stats.pages == 2
    assert stats.origins == page_size * stats.pages

    spy_request.assert_has_calls(
        [
            mocker.call(
                "GET",
                lister.NPM_API_CHANGES_URL,
                params={"limit": 2, "since": "0"},
            ),
            mocker.call(
                "GET",
                lister.NPM_API_CHANGES_URL,
                params={"limit": 2, "since": "2"},
            ),
        ]
    )

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    assert {origin.url: origin.last_update for origin in scheduler_origins} == {
        "https://www.npmjs.com/package/overlay-fishnet": lister.listing_date,
        "https://www.npmjs.com/package/shopping_site_detect": lister.listing_date,
        "https://www.npmjs.com/package/tinyviewpager": lister.listing_date,
        "https://www.npmjs.com/package/ubase-ext-wecloud": lister.listing_date,
    }

    assert lister.get_state_from_scheduler() == NpmListerState()


def test_npm_lister_incremental(
    swh_scheduler,
    requests_mock,
    mocker,
    npm_changes_page1,
    npm_changes_page2,
):
    """Simulate an incremental listing of four npm packages in two pages"""
    page_size = 2
    lister = NpmLister(scheduler=swh_scheduler, page_size=page_size, incremental=True)
    first_listing_date = lister.listing_date

    requests_mock.get(
        lister.NPM_API_CHANGES_URL,
        [
            {"json": npm_changes_page1},
            {"json": {"results": []}},
        ],
        additional_matcher=_match_request,
    )

    spy_request = mocker.spy(lister.session, "request")

    assert lister.get_state_from_scheduler() == NpmListerState()

    stats = lister.run()
    assert stats.pages == 1
    assert stats.origins == page_size * stats.pages

    last_seq = npm_changes_page1["results"][-1]["seq"]

    spy_request.assert_has_calls(
        [
            mocker.call(
                "GET",
                lister.NPM_API_CHANGES_URL,
                params={"limit": 2, "since": "0"},
            ),
            mocker.call(
                "GET",
                lister.NPM_API_CHANGES_URL,
                params={"limit": 2, "since": "2"},
            ),
        ]
    )

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    assert {origin.url: origin.last_update for origin in scheduler_origins} == {
        "https://www.npmjs.com/package/overlay-fishnet": first_listing_date,
        "https://www.npmjs.com/package/shopping_site_detect": first_listing_date,
    }

    assert lister.get_state_from_scheduler() == NpmListerState(last_seq=last_seq)

    lister = NpmLister(scheduler=swh_scheduler, page_size=page_size, incremental=True)
    second_listing_date = lister.listing_date

    requests_mock.get(
        lister.NPM_API_CHANGES_URL,
        [
            {"json": npm_changes_page2},
            {"json": {"results": []}},
        ],
        additional_matcher=_match_request,
    )

    spy_request = mocker.spy(lister.session, "request")

    stats = lister.run()
    assert stats.pages == 1
    assert stats.origins == page_size * stats.pages

    last_seq = npm_changes_page2["results"][-1]["seq"]

    spy_request.assert_has_calls(
        [
            mocker.call(
                "GET",
                lister.NPM_API_CHANGES_URL,
                params={"limit": 2, "since": "2"},
            ),
            mocker.call(
                "GET",
                lister.NPM_API_CHANGES_URL,
                params={"limit": 2, "since": "4"},
            ),
        ]
    )

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    assert {origin.url: origin.last_update for origin in scheduler_origins} == {
        "https://www.npmjs.com/package/overlay-fishnet": first_listing_date,
        "https://www.npmjs.com/package/shopping_site_detect": first_listing_date,
        "https://www.npmjs.com/package/tinyviewpager": second_listing_date,
        "https://www.npmjs.com/package/ubase-ext-wecloud": second_listing_date,
    }

    assert lister.get_state_from_scheduler() == NpmListerState(last_seq=last_seq)


def test_npm_lister_http_error(
    swh_scheduler,
    requests_mock,
    mocker,
):
    lister = NpmLister(scheduler=swh_scheduler)

    requests_mock.get(lister.NPM_API_CHANGES_URL, status_code=500)

    with pytest.raises(HTTPError):
        lister.run()
