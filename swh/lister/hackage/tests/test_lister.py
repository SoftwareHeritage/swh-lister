# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import functools
import json
from pathlib import Path
from urllib.parse import unquote, urlparse

import iso8601

from swh.lister.hackage.lister import HackageLister, HackageListerState


def json_callback(request, context, datadir, visit=0):
    """Callback for requests_mock that load a json file regarding a page number"""
    unquoted_url = unquote(request.url)
    url = urlparse(unquoted_url)
    page = request.json()["page"]

    dirname = "%s_%s" % (url.scheme, url.hostname)
    filename = url.path[1:]
    if filename.endswith("/"):
        filename = filename[:-1]
    filename = filename.replace("/", "_")
    filepath = Path(datadir, dirname, f"{filename}_{page}")

    if visit > 0:
        filepath = filepath.parent / f"{filepath.stem}_visit{visit}"
    return json.loads(filepath.read_text())


def test_hackage_lister(swh_scheduler, requests_mock, datadir):
    """Assert a full listing of 3 pages of 50 origins"""

    requests_mock.post(
        url="https://hackage.haskell.org/packages/search",
        status_code=200,
        json=functools.partial(json_callback, datadir=datadir),
    )

    expected_origins = []

    for page in [0, 1, 2]:
        data = json.loads(
            Path(
                datadir, "https_hackage.haskell.org", f"packages_search_{page}"
            ).read_text()
        )
        for entry in data["pageContents"]:
            pkgname = entry["name"]["display"]
            expected_origins.append(
                {"url": f"https://hackage.haskell.org/package/{pkgname}"}
            )

    lister = HackageLister(scheduler=swh_scheduler)
    res = lister.run()

    assert res.pages == 3
    assert res.origins == res.pages * 50

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    assert len(scheduler_origins) == len(expected_origins)

    assert {
        (
            scheduled.visit_type,
            scheduled.url,
        )
        for scheduled in scheduler_origins
    } == {
        (
            "hackage",
            expected["url"],
        )
        for expected in expected_origins
    }


def test_hackage_lister_pagination_49(swh_scheduler, requests_mock, datadir):
    """Test Pagination

    Page size is 50, lister returns 1 page when origins < page size
    """
    requests_mock.post(
        url="https://fake49.haskell.org/packages/search",
        status_code=200,
        json=functools.partial(json_callback, datadir=datadir),
    )
    lister = HackageLister(scheduler=swh_scheduler, url="https://fake49.haskell.org/")
    pages = list(lister.get_pages())
    # there should be 1 page with 49 entries
    assert len(pages) == 1
    assert len(pages[0]) == 49


def test_hackage_lister_pagination_51(swh_scheduler, requests_mock, datadir):
    """Test Pagination

    Page size is 50, lister returns 2 page when origins > page size
    """
    requests_mock.post(
        url="https://fake51.haskell.org/packages/search",
        status_code=200,
        json=functools.partial(json_callback, datadir=datadir),
    )
    lister = HackageLister(scheduler=swh_scheduler, url="https://fake51.haskell.org/")
    pages = list(lister.get_pages())
    # there should be 2 pages with 50 + 1 entries
    assert len(pages) == 2
    assert len(pages[0]) == 50
    assert len(pages[1]) == 1


def test_hackage_lister_incremental(swh_scheduler, requests_mock, datadir):
    """Test incremental lister

    * First run, full listing, 3 pages, 150 origins
    * Second run, 1 page, 3 new or updated origins
    * Third run, nothing new, 0 page, 0 origins
    """

    mock_url = "https://hackage.haskell.org/packages/search"

    # first run
    requests_mock.post(
        url=mock_url,
        status_code=200,
        json=functools.partial(json_callback, datadir=datadir),
    )
    lister = HackageLister(scheduler=swh_scheduler)
    # force lister.last_listing_date to not being 'now'
    lister.state.last_listing_date = iso8601.parse_date("2022-08-26T02:27:45.073759Z")
    lister.set_state_in_scheduler()
    assert lister.get_state_from_scheduler() == HackageListerState(
        last_listing_date=iso8601.parse_date("2022-08-26T02:27:45.073759Z")
    )

    first = lister.run()
    assert first.pages == 3
    assert first.origins == 3 * 50
    # 3 http requests done
    assert len(requests_mock.request_history) == 3
    for rh in requests_mock.request_history:
        assert rh.json()["searchQuery"] == "(deprecated:any)(lastUpload >= 2022-08-26)"

    # second run
    requests_mock.post(
        url=mock_url,
        status_code=200,
        json=functools.partial(json_callback, datadir=datadir, visit=1),
    )
    lister = HackageLister(scheduler=swh_scheduler)
    # force lister.last_listing_date to not being 'now'
    lister.state.last_listing_date = iso8601.parse_date(
        "2022-09-30T08:00:34.348551203Z"
    )
    lister.set_state_in_scheduler()
    assert lister.get_state_from_scheduler() == HackageListerState(
        last_listing_date=iso8601.parse_date("2022-09-30T08:00:34.348551203Z")
    )

    second = lister.run()
    assert second.pages == 1
    assert second.origins == 3

    assert len(requests_mock.request_history) == 3 + 1
    # Check the first three ones, should be the same as first run
    for i in range(3):
        assert (
            requests_mock.request_history[i].json()["searchQuery"]
            == "(deprecated:any)(lastUpload >= 2022-08-26)"
        )
    # Check the last one, lastUpload should be the same as second run
    assert (
        requests_mock.last_request.json()["searchQuery"]
        == "(deprecated:any)(lastUpload >= 2022-09-30)"
    )

    # third run (no update since last run, no new or updated origins but one http requests
    # with no results)
    requests_mock.post(
        url=mock_url,
        status_code=200,
        json=functools.partial(json_callback, datadir=datadir, visit=2),
    )
    lister = HackageLister(scheduler=swh_scheduler)
    third = lister.run()

    assert third.pages == 0
    assert third.origins == 0
    assert lister.get_state_from_scheduler() == HackageListerState(
        last_listing_date=lister.state.last_listing_date
    )
    assert len(requests_mock.request_history) == 3 + 1 + 1
