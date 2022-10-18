# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

# flake8: noqa: B950

from pathlib import Path

import iso8601
import pytest

from swh.lister.rubygems.lister import RubyGemsLister
from swh.scheduler.model import ListedOrigin

DUMP_FILEPATH = "production/public_postgresql/2022.10.06.06.10.05/public_postgresql.tar"


@pytest.fixture
def expected_listed_origins():
    return [
        {
            "url": "https://rubygems.org/gems/haar_joke",
            "visit_type": "rubygems",
            "last_update": iso8601.parse_date("2016-11-05T00:00:00+00:00"),
            "extra_loader_arguments": {
                "artifacts": [
                    {
                        "url": "https://rubygems.org/downloads/haar_joke-0.0.2.gem",
                        "length": 8704,
                        "version": "0.0.2",
                        "filename": "haar_joke-0.0.2.gem",
                        "checksums": {
                            "sha256": "85a8cf5f41890e9605265eeebfe9e99aa0350a01a3c799f9f55a0615a31a2f5f"
                        },
                    },
                    {
                        "url": "https://rubygems.org/downloads/haar_joke-0.0.1.gem",
                        "length": 8704,
                        "version": "0.0.1",
                        "filename": "haar_joke-0.0.1.gem",
                        "checksums": {
                            "sha256": "a2ee7052fb8ffcfc4ec0fdb77fae9a36e473f859af196a36870a0f386b5ab55e"
                        },
                    },
                ],
                "rubygem_metadata": [
                    {
                        "date": "2016-11-05T00:00:00+00:00",
                        "authors": "Gemma Gotch",
                        "version": "0.0.2",
                        "extrinsic_metadata_url": "https://rubygems.org/api/v2/rubygems/haar_joke/versions/0.0.2.json",
                    },
                    {
                        "date": "2016-07-23T00:00:00+00:00",
                        "authors": "Gemma Gotch",
                        "version": "0.0.1",
                        "extrinsic_metadata_url": "https://rubygems.org/api/v2/rubygems/haar_joke/versions/0.0.1.json",
                    },
                ],
            },
        },
        {
            "url": "https://rubygems.org/gems/l33tify",
            "visit_type": "rubygems",
            "last_update": iso8601.parse_date("2014-11-14T00:00:00+00:00"),
            "extra_loader_arguments": {
                "artifacts": [
                    {
                        "url": "https://rubygems.org/downloads/l33tify-0.0.2.gem",
                        "length": 6144,
                        "version": "0.0.2",
                        "filename": "l33tify-0.0.2.gem",
                        "checksums": {
                            "sha256": "0087a21fb6161bba8892df40de3b5e27404f941658084413b8fde49db2bc7c9f"
                        },
                    },
                    {
                        "url": "https://rubygems.org/downloads/l33tify-0.0.3.gem",
                        "length": 6144,
                        "version": "0.0.3",
                        "filename": "l33tify-0.0.3.gem",
                        "checksums": {
                            "sha256": "4502097ddf2657d561ce0f527ef1f49f1658c8a0968ab8cc853273138f8382a2"
                        },
                    },
                    {
                        "url": "https://rubygems.org/downloads/l33tify-0.0.1.gem",
                        "length": 6144,
                        "version": "0.0.1",
                        "filename": "l33tify-0.0.1.gem",
                        "checksums": {
                            "sha256": "5abfb737ce5cf561726f2f7cc1ba0f0e4f865f8b7283192e05eb3f246d3dbbca"
                        },
                    },
                ],
                "rubygem_metadata": [
                    {
                        "date": "2014-11-14T00:00:00+00:00",
                        "authors": "E Alexander Liedtke",
                        "version": "0.0.2",
                        "extrinsic_metadata_url": "https://rubygems.org/api/v2/rubygems/l33tify/versions/0.0.2.json",
                    },
                    {
                        "date": "2014-11-14T00:00:00+00:00",
                        "authors": "E Alexander Liedtke",
                        "version": "0.0.3",
                        "extrinsic_metadata_url": "https://rubygems.org/api/v2/rubygems/l33tify/versions/0.0.3.json",
                    },
                    {
                        "date": "2014-11-14T00:00:00+00:00",
                        "authors": "E Alexander Liedtke",
                        "version": "0.0.1",
                        "extrinsic_metadata_url": "https://rubygems.org/api/v2/rubygems/l33tify/versions/0.0.1.json",
                    },
                ],
            },
        },
    ]


@pytest.fixture(autouse=True)
def network_requests_mock(datadir, requests_mock):
    requests_mock.get(
        RubyGemsLister.RUBY_GEMS_POSTGRES_DUMP_LIST_URL,
        content=Path(datadir, "rubygems_dumps.xml").read_bytes(),
    )
    content = Path(datadir, "rubygems_pgsql_dump.tar").read_bytes()
    requests_mock.get(
        f"{RubyGemsLister.RUBY_GEMS_POSTGRES_DUMP_BASE_URL}/{DUMP_FILEPATH}",
        content=content,
        headers={"content-length": str(len(content))},
    )


@pytest.mark.db
def test_rubygems_lister(swh_scheduler, expected_listed_origins):
    lister = RubyGemsLister(scheduler=swh_scheduler)
    res = lister.run()

    assert res.pages == 2
    assert res.origins == 2

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    assert [
        {
            "url": origin.url,
            "visit_type": origin.visit_type,
            "last_update": origin.last_update,
            "extra_loader_arguments": origin.extra_loader_arguments,
        }
        for origin in scheduler_origins
    ] == expected_listed_origins
