# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from pathlib import Path

from swh.lister.crates.lister import CratesLister
from swh.lister.crates.tests import prepare_repository_from_archive

expected_origins = [
    {
        "name": "rand",
        "version": "0.1.1",
        "checksum": "48a45b46c2a8c38348adb1205b13c3c5eb0174e0c0fec52cc88e9fb1de14c54d",
        "url": "https://static.crates.io/crates/rand/rand-0.1.1.crate",
    },
    {
        "name": "rand",
        "version": "0.1.2",
        "checksum": "6e229ed392842fa93c1d76018d197b7e1b74250532bafb37b0e1d121a92d4cf7",
        "url": "https://static.crates.io/crates/rand/rand-0.1.2.crate",
    },
    {
        "name": "regex",
        "version": "0.1.0",
        "checksum": "f0ff1ca641d3c9a2c30464dac30183a8b91cdcc959d616961be020cdea6255c5",
        "url": "https://static.crates.io/crates/regex/regex-0.1.0.crate",
    },
    {
        "name": "regex",
        "version": "0.1.1",
        "checksum": "a07bef996bd38a73c21a8e345d2c16848b41aa7ec949e2fedffe9edf74cdfb36",
        "url": "https://static.crates.io/crates/regex/regex-0.1.1.crate",
    },
    {
        "name": "regex",
        "version": "0.1.2",
        "checksum": "343bd0171ee23346506db6f4c64525de6d72f0e8cc533f83aea97f3e7488cbf9",
        "url": "https://static.crates.io/crates/regex/regex-0.1.2.crate",
    },
    {
        "name": "regex",
        "version": "0.1.3",
        "checksum": "defb220c4054ca1b95fe8b0c9a6e782dda684c1bdf8694df291733ae8a3748e3",
        "url": "https://static.crates.io/crates/regex/regex-0.1.3.crate",
    },
    {
        "name": "regex-syntax",
        "version": "0.1.0",
        "checksum": "398952a2f6cd1d22bc1774fd663808e32cf36add0280dee5cdd84a8fff2db944",
        "url": "https://static.crates.io/crates/regex-syntax/regex-syntax-0.1.0.crate",
    },
]


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
    assert res.origins == 7

    expected_origins_sorted = sorted(expected_origins, key=lambda x: x.get("url"))
    scheduler_origins_sorted = sorted(
        swh_scheduler.get_listed_origins(lister.lister_obj.id).results,
        key=lambda x: x.url,
    )

    for scheduled, expected in zip(scheduler_origins_sorted, expected_origins_sorted):
        assert scheduled.visit_type == "rust-crate"
        assert scheduled.url == expected.get("url")
        assert scheduled.extra_loader_arguments.get("name") == expected.get("name")
        assert scheduled.extra_loader_arguments.get("version") == expected.get(
            "version"
        )
        assert scheduled.extra_loader_arguments.get("checksum") == expected.get(
            "checksum"
        )

    assert len(scheduler_origins_sorted) == len(expected_origins_sorted)
