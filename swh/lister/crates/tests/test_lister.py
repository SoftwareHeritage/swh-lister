# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from pathlib import Path

from dulwich.repo import Repo

from swh.lister.crates.lister import CratesLister, CratesListerState
from swh.lister.crates.tests import prepare_repository_from_archive

expected_origins = [
    {
        "url": "https://crates.io/api/v1/crates/rand",
        "artifacts": [
            {
                "checksums": {
                    "sha256": "48a45b46c2a8c38348adb1205b13c3c5eb0174e0c0fec52cc88e9fb1de14c54d",  # noqa: B950
                },
                "filename": "rand-0.1.1.crate",
                "url": "https://static.crates.io/crates/rand/rand-0.1.1.crate",
                "version": "0.1.1",
            },
            {
                "checksums": {
                    "sha256": "6e229ed392842fa93c1d76018d197b7e1b74250532bafb37b0e1d121a92d4cf7",  # noqa: B950
                },
                "filename": "rand-0.1.2.crate",
                "url": "https://static.crates.io/crates/rand/rand-0.1.2.crate",
                "version": "0.1.2",
            },
        ],
        "metadata": [
            {
                "version": "0.1.1",
                "yanked": False,
            },
            {
                "version": "0.1.2",
                "yanked": False,
            },
        ],
    },
    {
        "url": "https://crates.io/api/v1/crates/regex",
        "artifacts": [
            {
                "checksums": {
                    "sha256": "f0ff1ca641d3c9a2c30464dac30183a8b91cdcc959d616961be020cdea6255c5",  # noqa: B950
                },
                "filename": "regex-0.1.0.crate",
                "url": "https://static.crates.io/crates/regex/regex-0.1.0.crate",
                "version": "0.1.0",
            },
            {
                "checksums": {
                    "sha256": "a07bef996bd38a73c21a8e345d2c16848b41aa7ec949e2fedffe9edf74cdfb36",  # noqa: B950
                },
                "filename": "regex-0.1.1.crate",
                "url": "https://static.crates.io/crates/regex/regex-0.1.1.crate",
                "version": "0.1.1",
            },
            {
                "checksums": {
                    "sha256": "343bd0171ee23346506db6f4c64525de6d72f0e8cc533f83aea97f3e7488cbf9",  # noqa: B950
                },
                "filename": "regex-0.1.2.crate",
                "url": "https://static.crates.io/crates/regex/regex-0.1.2.crate",
                "version": "0.1.2",
            },
            {
                "checksums": {
                    "sha256": "defb220c4054ca1b95fe8b0c9a6e782dda684c1bdf8694df291733ae8a3748e3",  # noqa: B950
                },
                "filename": "regex-0.1.3.crate",
                "url": "https://static.crates.io/crates/regex/regex-0.1.3.crate",
                "version": "0.1.3",
            },
        ],
        "metadata": [
            {
                "version": "0.1.0",
                "yanked": False,
            },
            {
                "version": "0.1.1",
                "yanked": False,
            },
            {
                "version": "0.1.2",
                "yanked": False,
            },
            {
                "version": "0.1.3",
                "yanked": False,
            },
        ],
    },
    {
        "url": "https://crates.io/api/v1/crates/regex-syntax",
        "artifacts": [
            {
                "checksums": {
                    "sha256": "398952a2f6cd1d22bc1774fd663808e32cf36add0280dee5cdd84a8fff2db944",  # noqa: B950
                },
                "filename": "regex-syntax-0.1.0.crate",
                "url": "https://static.crates.io/crates/regex-syntax/regex-syntax-0.1.0.crate",
                "version": "0.1.0",
            },
        ],
        "metadata": [
            {
                "version": "0.1.0",
                "yanked": False,
            },
        ],
    },
]


expected_origins_incremental = [expected_origins[1], expected_origins[2]]


def test_crates_lister(datadir, tmp_path, swh_scheduler):
    archive_path = Path(datadir, "fake-crates-repository.tar.gz")
    repo_url = prepare_repository_from_archive(
        archive_path, "crates.io-index", tmp_path
    )

    lister = CratesLister(scheduler=swh_scheduler)
    lister.INDEX_REPOSITORY_URL = repo_url
    lister.DESTINATION_PATH = tmp_path.parent / "crates.io-index-tests"

    res = lister.run()

    assert res.pages == 3
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


def test_crates_lister_incremental(datadir, tmp_path, swh_scheduler):
    archive_path = Path(datadir, "fake-crates-repository.tar.gz")
    repo_url = prepare_repository_from_archive(
        archive_path, "crates.io-index", tmp_path
    )

    lister = CratesLister(scheduler=swh_scheduler)
    lister.INDEX_REPOSITORY_URL = repo_url
    lister.DESTINATION_PATH = tmp_path.parent / "crates.io-index-tests"
    # The lister has not run yet, get the index repository
    lister.get_index_repository()
    # Set a CratesListerState with a last commit value to force incremental case
    repo = Repo(lister.DESTINATION_PATH)
    # Lets set this last commit to third one from head
    step = list(repo.get_walker(max_entries=3))[-1]
    last_commit_state = CratesListerState(last_commit=step.commit.id.decode())
    lister.state = last_commit_state

    res = lister.run()

    assert res.pages == 2
    assert res.origins == 2

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
        for expected in sorted(
            expected_origins_incremental, key=lambda expected: expected["url"]
        )
    ]


def test_crates_lister_incremental_nothing_new(datadir, tmp_path, swh_scheduler):
    """Ensure incremental mode runs fine when the repository last commit is the same
    than lister.state.las-_commit"""
    archive_path = Path(datadir, "fake-crates-repository.tar.gz")
    repo_url = prepare_repository_from_archive(
        archive_path, "crates.io-index", tmp_path
    )

    lister = CratesLister(scheduler=swh_scheduler)
    lister.INDEX_REPOSITORY_URL = repo_url
    lister.DESTINATION_PATH = tmp_path.parent / "crates.io-index-tests"
    lister.get_index_repository()

    repo = Repo(lister.DESTINATION_PATH)

    # Set a CratesListerState with a last commit value to force incremental case
    last_commit_state = CratesListerState(last_commit=repo.head().decode())
    lister.state = last_commit_state

    res = lister.run()

    assert res.pages == 0
    assert res.origins == 0


def test_crates_lister_repository_cleanup(datadir, tmp_path, swh_scheduler):
    archive_path = Path(datadir, "fake-crates-repository.tar.gz")
    repo_url = prepare_repository_from_archive(
        archive_path, "crates.io-index", tmp_path
    )

    lister = CratesLister(scheduler=swh_scheduler)
    lister.INDEX_REPOSITORY_URL = repo_url
    lister.DESTINATION_PATH = tmp_path.parent / "crates.io-index-tests"

    lister.run()
    # Repository directory should not exists after the lister runs
    assert not lister.DESTINATION_PATH.exists()
