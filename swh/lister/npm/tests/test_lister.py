# Copyright (C) 2018-2021 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from itertools import chain
import json
from pathlib import Path

import iso8601
import pytest
from requests.exceptions import HTTPError

from swh.lister import USER_AGENT
from swh.lister.npm.lister import NpmLister, NpmListerState


@pytest.fixture
def npm_full_listing_page1(datadir):
    return json.loads(Path(datadir, "npm_full_page1.json").read_text())


@pytest.fixture
def npm_full_listing_page2(datadir):
    return json.loads(Path(datadir, "npm_full_page2.json").read_text())


@pytest.fixture
def npm_incremental_listing_page1(datadir):
    return json.loads(Path(datadir, "npm_incremental_page1.json").read_text())


@pytest.fixture
def npm_incremental_listing_page2(datadir):
    return json.loads(Path(datadir, "npm_incremental_page2.json").read_text())


def _check_listed_npm_packages(lister, packages, scheduler_origins):
    for package in packages:
        package_name = package["doc"]["name"]
        latest_version = package["doc"]["dist-tags"]["latest"]
        package_last_update = iso8601.parse_date(package["doc"]["time"][latest_version])
        origin_url = lister.PACKAGE_URL_TEMPLATE.format(package_name=package_name)

        scheduler_origin = [o for o in scheduler_origins if o.url == origin_url]
        assert scheduler_origin
        assert scheduler_origin[0].last_update == package_last_update


def _match_request(request):
    return request.headers.get("User-Agent") == USER_AGENT


def _url_params(page_size, **kwargs):
    params = {"limit": page_size, "include_docs": "true"}
    params.update(**kwargs)
    return params


def test_npm_lister_full(
    swh_scheduler, requests_mock, mocker, npm_full_listing_page1, npm_full_listing_page2
):
    """Simulate a full listing of four npm packages in two pages"""
    page_size = 2
    lister = NpmLister(scheduler=swh_scheduler, page_size=page_size, incremental=False)

    requests_mock.get(
        lister.API_FULL_LISTING_URL,
        [{"json": npm_full_listing_page1}, {"json": npm_full_listing_page2},],
        additional_matcher=_match_request,
    )

    spy_get = mocker.spy(lister.session, "get")

    stats = lister.run()
    assert stats.pages == 2
    assert stats.origins == page_size * stats.pages

    spy_get.assert_has_calls(
        [
            mocker.call(
                lister.API_FULL_LISTING_URL,
                params=_url_params(page_size + 1, startkey='""'),
            ),
            mocker.call(
                lister.API_FULL_LISTING_URL,
                params=_url_params(
                    page_size + 1,
                    startkey=f'"{npm_full_listing_page1["rows"][-1]["id"]}"',
                ),
            ),
        ]
    )

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    _check_listed_npm_packages(
        lister,
        chain(npm_full_listing_page1["rows"][:-1], npm_full_listing_page2["rows"]),
        scheduler_origins,
    )

    assert lister.get_state_from_scheduler() == NpmListerState()


def test_npm_lister_incremental(
    swh_scheduler,
    requests_mock,
    mocker,
    npm_incremental_listing_page1,
    npm_incremental_listing_page2,
):
    """Simulate an incremental listing of four npm packages in two pages"""
    page_size = 2
    lister = NpmLister(scheduler=swh_scheduler, page_size=page_size, incremental=True)

    requests_mock.get(
        lister.API_INCREMENTAL_LISTING_URL,
        [
            {"json": npm_incremental_listing_page1},
            {"json": npm_incremental_listing_page2},
            {"json": {"results": []}},
        ],
        additional_matcher=_match_request,
    )

    spy_get = mocker.spy(lister.session, "get")

    assert lister.get_state_from_scheduler() == NpmListerState()

    stats = lister.run()
    assert stats.pages == 2
    assert stats.origins == page_size * stats.pages

    last_seq = npm_incremental_listing_page2["results"][-1]["seq"]

    spy_get.assert_has_calls(
        [
            mocker.call(
                lister.API_INCREMENTAL_LISTING_URL,
                params=_url_params(page_size, since="0"),
            ),
            mocker.call(
                lister.API_INCREMENTAL_LISTING_URL,
                params=_url_params(
                    page_size,
                    since=str(npm_incremental_listing_page1["results"][-1]["seq"]),
                ),
            ),
            mocker.call(
                lister.API_INCREMENTAL_LISTING_URL,
                params=_url_params(page_size, since=str(last_seq)),
            ),
        ]
    )

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    _check_listed_npm_packages(
        lister,
        chain(
            npm_incremental_listing_page1["results"],
            npm_incremental_listing_page2["results"],
        ),
        scheduler_origins,
    )

    assert lister.get_state_from_scheduler() == NpmListerState(last_seq=last_seq)


def test_npm_lister_incremental_restart(
    swh_scheduler, requests_mock, mocker,
):
    """Check incremental npm listing will restart from saved state"""
    page_size = 2
    last_seq = 67
    lister = NpmLister(scheduler=swh_scheduler, page_size=page_size, incremental=True)
    lister.state = NpmListerState(last_seq=last_seq)

    requests_mock.get(lister.API_INCREMENTAL_LISTING_URL, json={"results": []})

    spy_get = mocker.spy(lister.session, "get")

    lister.run()

    spy_get.assert_called_with(
        lister.API_INCREMENTAL_LISTING_URL,
        params=_url_params(page_size, since=str(last_seq)),
    )


def test_npm_lister_http_error(
    swh_scheduler, requests_mock, mocker,
):
    lister = NpmLister(scheduler=swh_scheduler)

    requests_mock.get(lister.API_FULL_LISTING_URL, status_code=500)

    with pytest.raises(HTTPError):
        lister.run()
