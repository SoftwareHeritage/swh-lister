# Copyright (C) 2022-2024  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import datetime
from pathlib import Path

import iso8601

from swh.core.retry import WAIT_EXP_BASE
from swh.lister.golang.lister import GolangLister, GolangStateType
from swh.lister.tests.utils import assert_sleep_calls

# https://pkg.go.dev prefix omitted
expected_listed = [
    ("collectd.org", "2019-04-11T18:47:25.450546+00:00"),
    (
        "github.com/blang/semver",
        "2019-04-15T13:54:39.107258+00:00",
    ),
    (
        "github.com/bmizerany/pat",
        "2019-04-11T18:47:29.390564+00:00",
    ),
    (
        "github.com/djherbis/buffer",
        "2019-04-11T18:47:29.974874+00:00",
    ),
    (
        "github.com/djherbis/nio",
        "2019-04-11T18:47:32.283312+00:00",
    ),
    (
        "github.com/gobuffalo/buffalo-plugins",
        "2019-04-15T13:54:34.222985+00:00",
    ),
    (
        "github.com/gobuffalo/buffalo-pop",
        "2019-04-15T13:54:39.135792+00:00",
    ),
    (
        "github.com/gobuffalo/clara",
        "2019-04-15T13:54:40.651916+00:00",
    ),
    (
        "github.com/gobuffalo/genny",
        "2019-04-15T13:54:37.841547+00:00",
    ),
    (
        "github.com/gobuffalo/packr",
        "2019-04-15T13:54:35.688900+00:00",
    ),
    (
        "github.com/markbates/refresh",
        "2019-04-15T13:54:35.250835+00:00",
    ),
    (
        "github.com/mitchellh/go-homedir",
        "2019-04-15T13:54:35.678214+00:00",
    ),
    (
        "github.com/nats-io/nuid",
        "2019-04-11T18:47:28.102348+00:00",
    ),
    (
        "github.com/oklog/ulid",
        "2019-04-11T18:47:23.234198+00:00",
    ),
    (
        "github.com/pkg/errors",
        "2019-04-18T02:07:41.336899+00:00",
    ),
    (
        "golang.org/x/sys",
        "2019-04-15T13:54:37.555525+00:00",
    ),
    ("golang.org/x/text", "2019-04-10T19:08:52.997264+00:00"),
    # only one x/tools listed even though there are two version, and only the
    # latest one's timestamp is used.
    (
        "golang.org/x/tools",
        "2019-04-15T13:54:41.905064+00:00",
    ),
]


def _generate_responses(datadir, requests_mock):
    responses = []
    for file in Path(datadir).glob("page-*.txt"):
        # Test that throttling and server errors are retries
        responses.append({"text": "", "status_code": 429})
        responses.append({"text": "", "status_code": 500})
        # Also test that the lister appropriately gets out of the infinite loop
        responses.append({"text": file.read_text(), "status_code": 200})

    requests_mock.get(GolangLister.GOLANG_MODULES_INDEX_URL, responses)


def test_golang_lister(swh_scheduler, mocker, requests_mock, datadir, mock_sleep):
    # first listing, should return one origin per package
    lister = GolangLister(scheduler=swh_scheduler)

    _generate_responses(datadir, requests_mock)

    stats = lister.run()

    assert stats.pages == 3
    # The two `golang.org/x/tools` versions are *not* listed as separate origins
    assert stats.origins == 18

    scheduler_origins = sorted(
        swh_scheduler.get_listed_origins(lister.lister_obj.id).results,
        key=lambda x: x.url,
    )

    for scheduled, (url, timestamp) in zip(scheduler_origins, expected_listed):
        assert scheduled.url == f"https://pkg.go.dev/{url}"
        assert scheduled.last_update == iso8601.parse_date(timestamp)
        assert scheduled.visit_type == "golang"

    assert len(scheduler_origins) == len(expected_listed)

    # Test `time.sleep` is called with exponential retries
    assert_sleep_calls(
        mocker, mock_sleep, [1, WAIT_EXP_BASE, 1, WAIT_EXP_BASE, 1, WAIT_EXP_BASE]
    )

    # doing it all again (without incremental) should give us the same result
    lister = GolangLister(scheduler=swh_scheduler)

    _generate_responses(datadir, requests_mock)
    stats = lister.run()

    assert stats.pages == 3
    assert stats.origins == 18


def test_golang_lister_incremental(swh_scheduler, requests_mock, datadir, mocker):
    # first listing, should return one origin per package
    lister = GolangLister(scheduler=swh_scheduler, incremental=True)
    mock = mocker.spy(lister, "get_single_page")

    responses = [
        {"text": Path(datadir, "page-1.txt").read_text(), "status_code": 200},
    ]
    requests_mock.get(GolangLister.GOLANG_MODULES_INDEX_URL, responses)

    stats = lister.run()

    page1_last_timestamp = datetime.datetime(
        2019, 4, 11, 18, 47, 29, 390564, tzinfo=datetime.timezone.utc
    )
    page2_last_timestamp = datetime.datetime(
        2019, 4, 15, 13, 54, 35, 250835, tzinfo=datetime.timezone.utc
    )
    page3_last_timestamp = datetime.datetime(
        2019, 4, 18, 2, 7, 41, 336899, tzinfo=datetime.timezone.utc
    )
    mock.assert_has_calls(
        [
            # First call has no state
            mocker.call(since=None),
            # Second call is the last timestamp in the listed page
            mocker.call(since=page1_last_timestamp),
        ]
    )

    assert lister.get_state_from_scheduler() == GolangStateType(
        last_seen=page1_last_timestamp
    )

    assert stats.pages == 1
    assert stats.origins == 5

    # Incremental should list nothing
    lister = GolangLister(scheduler=swh_scheduler, incremental=True)
    mock = mocker.spy(lister, "get_single_page")
    stats = lister.run()
    mock.assert_has_calls([mocker.call(since=page1_last_timestamp)])
    assert stats.pages == 0
    assert stats.origins == 0

    # Add more responses
    responses = [
        {"text": Path(datadir, "page-2.txt").read_text(), "status_code": 200},
    ]

    requests_mock.get(GolangLister.GOLANG_MODULES_INDEX_URL, responses)

    # Incremental should list new page
    lister = GolangLister(scheduler=swh_scheduler, incremental=True)
    mock = mocker.spy(lister, "get_single_page")
    stats = lister.run()
    mock.assert_has_calls(
        [
            mocker.call(since=page1_last_timestamp),
            mocker.call(since=page2_last_timestamp),
        ]
    )
    assert stats.pages == 1
    assert stats.origins == 4

    # Incremental should list nothing again
    lister = GolangLister(scheduler=swh_scheduler, incremental=True)
    mock = mocker.spy(lister, "get_single_page")
    stats = lister.run()
    assert stats.pages == 0
    assert stats.origins == 0
    mock.assert_has_calls([mocker.call(since=page2_last_timestamp)])

    # Add yet more responses
    responses = [
        {"text": Path(datadir, "page-3.txt").read_text(), "status_code": 200},
    ]

    requests_mock.get(GolangLister.GOLANG_MODULES_INDEX_URL, responses)

    # Incremental should list new page again
    lister = GolangLister(scheduler=swh_scheduler, incremental=True)
    mock = mocker.spy(lister, "get_single_page")
    stats = lister.run()
    assert stats.pages == 1
    assert stats.origins == 9
    mock.assert_has_calls(
        [
            mocker.call(since=page2_last_timestamp),
            mocker.call(since=page3_last_timestamp),
        ]
    )

    # Incremental should list nothing one last time
    lister = GolangLister(scheduler=swh_scheduler, incremental=True)
    mock = mocker.spy(lister, "get_single_page")
    stats = lister.run()
    assert stats.pages == 0
    assert stats.origins == 0
    mock.assert_has_calls([mocker.call(since=page3_last_timestamp)])
