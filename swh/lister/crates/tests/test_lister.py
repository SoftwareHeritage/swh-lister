# Copyright (C) 2022-2024  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import iso8601
import pytest

from swh.lister.crates.lister import CratesLister, CratesListerState

expected_origins = [
    {
        "url": "https://crates.io/crates/rand",
        "artifacts": [
            {
                "version": "0.1.1",
                "checksums": {
                    "sha256": "48a45b46c2a8c38348adb1205b13c3c5eb0174e0c0fec52cc88e9fb1de14c54d",  # noqa: B950
                },
                "filename": "rand-0.1.1.crate",
                "url": "https://static.crates.io/crates/rand/rand-0.1.1.crate",
            },
            {
                "version": "0.1.2",
                "checksums": {
                    "sha256": "6e229ed392842fa93c1d76018d197b7e1b74250532bafb37b0e1d121a92d4cf7",  # noqa: B950
                },
                "filename": "rand-0.1.2.crate",
                "url": "https://static.crates.io/crates/rand/rand-0.1.2.crate",
            },
            {
                "version": "0.1.3-experimental",
                "checksums": {
                    "sha256": "d879626d5babe4ca6c4ec953d712e28d939672b325a4f9352f28ca3c82568a15",  # noqa: B950
                },
                "filename": "rand-0.1.3-experimental.crate",
                "url": "https://static.crates.io/crates/rand/rand-0.1.3-experimental.crate",
            },
        ],
    },
    {
        "url": "https://crates.io/crates/regex",
        "artifacts": [
            {
                "version": "0.1.0",
                "checksums": {
                    "sha256": "f0ff1ca641d3c9a2c30464dac30183a8b91cdcc959d616961be020cdea6255c5",  # noqa: B950
                },
                "filename": "regex-0.1.0.crate",
                "url": "https://static.crates.io/crates/regex/regex-0.1.0.crate",
            },
            {
                "version": "0.1.1",
                "checksums": {
                    "sha256": "a07bef996bd38a73c21a8e345d2c16848b41aa7ec949e2fedffe9edf74cdfb36",  # noqa: B950
                },
                "filename": "regex-0.1.1.crate",
                "url": "https://static.crates.io/crates/regex/regex-0.1.1.crate",
            },
            {
                "version": "0.1.2",
                "checksums": {
                    "sha256": "343bd0171ee23346506db6f4c64525de6d72f0e8cc533f83aea97f3e7488cbf9",  # noqa: B950
                },
                "filename": "regex-0.1.2.crate",
                "url": "https://static.crates.io/crates/regex/regex-0.1.2.crate",
            },
            {
                "version": "0.1.3",
                "checksums": {
                    "sha256": "defb220c4054ca1b95fe8b0c9a6e782dda684c1bdf8694df291733ae8a3748e3",  # noqa: B950
                },
                "filename": "regex-0.1.3.crate",
                "url": "https://static.crates.io/crates/regex/regex-0.1.3.crate",
            },
        ],
    },
    {
        "url": "https://crates.io/crates/regex-syntax",
        "artifacts": [
            {
                "version": "0.1.0",
                "checksums": {
                    "sha256": "398952a2f6cd1d22bc1774fd663808e32cf36add0280dee5cdd84a8fff2db944",  # noqa: B950
                },
                "filename": "regex-syntax-0.1.0.crate",
                "url": "https://static.crates.io/crates/regex-syntax/regex-syntax-0.1.0.crate",  # noqa: B950
            },
        ],
    },
]

expected_origins_incremental = {
    "url": "https://crates.io/crates/pin-project",
    "artifacts": [
        {
            "version": "1.0.12",
            "url": "https://static.crates.io/crates/pin-project/pin-project-1.0.12.crate",
            "filename": "pin-project-1.0.12.crate",
            "checksums": {
                "sha256": "ad29a609b6bcd67fee905812e544992d216af9d755757c05ed2d0e15a74c6ecc"
            },
        }
    ],
}


def test_crates_lister_is_new(swh_scheduler):
    lister = CratesLister(scheduler=swh_scheduler)

    index_last_update_state = CratesListerState(
        index_last_update=iso8601.parse_date("2022-08-15 13:52:11.642129")
    )
    lister.state = index_last_update_state

    assert lister.is_new("2022-07-15 13:52:11.642129") is False  # earlier
    assert lister.is_new("2022-08-15 13:52:11.642129") is False  # exactly equal
    assert lister.is_new("2022-09-15 13:52:11.642129") is True  # after


def test_crates_lister(datadir, tmp_path, swh_scheduler, requests_mock_datadir):
    lister = CratesLister(scheduler=swh_scheduler)
    res = lister.run()

    assert res.pages == 1
    assert res.origins == 3

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    assert [
        (
            scheduled.visit_type,
            scheduled.url,
            scheduled.extra_loader_arguments["artifacts"],
        )
        for scheduled in sorted(scheduler_origins, key=lambda scheduled: scheduled.url)
    ] == [
        (
            "crates",
            expected["url"],
            expected["artifacts"],
        )
        for expected in sorted(expected_origins, key=lambda expected: expected["url"])
    ]


def test_crates_lister_incremental(
    datadir, tmp_path, swh_scheduler, requests_mock_datadir_visits
):
    lister = CratesLister(scheduler=swh_scheduler)
    first = lister.run()

    assert first.pages == 1
    assert first.origins == 3

    second = lister.run()

    assert second.pages == 1
    assert second.origins == 1

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    expected_origins.append(expected_origins_incremental)

    assert [
        (
            scheduled.visit_type,
            scheduled.url,
            scheduled.extra_loader_arguments["artifacts"],
        )
        for scheduled in sorted(scheduler_origins, key=lambda scheduled: scheduled.url)
    ] == [
        (
            "crates",
            expected["url"],
            expected["artifacts"],
        )
        for expected in sorted(expected_origins, key=lambda expected: expected["url"])
    ]


def test_crates_lister_incremental_nothing_new(
    datadir, tmp_path, swh_scheduler, requests_mock_datadir
):
    """Ensure incremental mode runs fine when the repository last commit is the same
    than lister.state.last_commit"""
    lister = CratesLister(scheduler=swh_scheduler)
    lister.get_and_parse_db_dump()

    # Set a CratesListerState with a last commit value to force incremental case
    index_last_update_state = CratesListerState(
        index_last_update=iso8601.parse_date(lister.index_metadata["timestamp"])
    )
    lister.state = index_last_update_state

    res = lister.run()

    assert res.pages == 0
    assert res.origins == 0


def test_crates_lister_error_when_processing_crate(
    swh_scheduler, requests_mock_datadir, mocker
):
    """Lister state should not be recorded to scheduler is an error occurred
    when processing crate data."""
    lister = CratesLister(scheduler=swh_scheduler)
    mocker.patch.object(lister, "page_entry_dict").side_effect = IndexError()
    with pytest.raises(IndexError):
        lister.run()

    assert lister.get_state_from_scheduler().index_last_update is None
