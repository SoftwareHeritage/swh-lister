# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from datetime import datetime, timedelta, timezone

from swh.lister.puppet.lister import PuppetLister

# flake8: noqa: B950

expected_origins = [
    {
        "url": "https://forge.puppet.com/modules/electrical/file_concat",
        "artifacts": [
            {
                "url": "https://forgeapi.puppet.com/v3/files/electrical-file_concat-1.0.1.tar.gz",
                "version": "1.0.1",
                "filename": "electrical-file_concat-1.0.1.tar.gz",
                "last_update": "2015-04-17T01:03:46-07:00",
                "checksums": {
                    "md5": "74901a89544134478c2dfde5efbb7f14",
                    "sha256": "15e973613ea038d8a4f60bafe2d678f88f53f3624c02df3157c0043f4a400de6",
                },
            },
            {
                "url": "https://forgeapi.puppet.com/v3/files/electrical-file_concat-1.0.0.tar.gz",
                "version": "1.0.0",
                "filename": "electrical-file_concat-1.0.0.tar.gz",
                "last_update": "2015-04-09T12:03:13-07:00",
                "checksums": {
                    "length": 13289,
                },
            },
        ],
    },
    {
        "url": "https://forge.puppet.com/modules/puppetlabs/puppetdb",
        "artifacts": [
            {
                "url": "https://forgeapi.puppet.com/v3/files/puppetlabs-puppetdb-7.10.0.tar.gz",
                "version": "7.10.0",
                "filename": "puppetlabs-puppetdb-7.10.0.tar.gz",
                "last_update": "2021-12-16T14:57:46-08:00",
                "checksums": {
                    "md5": "e91a2074ca8d94a8b3ff7f6c8bbf12bc",
                    "sha256": "49b1a542fbd2a1378c16cb04809e0f88bf4f3e45979532294fb1f03f56c97fbb",
                },
            },
            {
                "url": "https://forgeapi.puppet.com/v3/files/puppetlabs-puppetdb-7.9.0.tar.gz",
                "version": "7.9.0",
                "filename": "puppetlabs-puppetdb-7.9.0.tar.gz",
                "last_update": "2021-06-24T07:48:54-07:00",
                "checksums": {
                    "length": 42773,
                },
            },
            {
                "url": "https://forgeapi.puppet.com/v3/files/puppetlabs-puppetdb-1.0.0.tar.gz",
                "version": "1.0.0",
                "filename": "puppetlabs-puppetdb-1.0.0.tar.gz",
                "last_update": "2012-09-19T16:51:22-07:00",
                "checksums": {
                    "length": 16336,
                },
            },
        ],
    },
    {
        "url": "https://forge.puppet.com/modules/saz/memcached",
        "artifacts": [
            {
                "url": "https://forgeapi.puppet.com/v3/files/saz-memcached-8.1.0.tar.gz",
                "version": "8.1.0",
                "filename": "saz-memcached-8.1.0.tar.gz",
                "last_update": "2022-07-11T03:34:55-07:00",
                "checksums": {
                    "md5": "aadf80fba5848909429eb002ee1927ea",
                    "sha256": "883d6186e91c2c3fed13ae2009c3aa596657f6707b76f1f7efc6203c6e4ae986",
                },
            },
            {
                "url": "https://forgeapi.puppet.com/v3/files/saz-memcached-1.0.0.tar.gz",
                "version": "1.0.0",
                "filename": "saz-memcached-1.0.0.tar.gz",
                "last_update": "2011-11-20T13:40:30-08:00",
                "checksums": {
                    "length": 2472,
                },
            },
        ],
    },
]


def test_puppet_lister(datadir, requests_mock_datadir, swh_scheduler):
    lister = PuppetLister(scheduler=swh_scheduler)
    res = lister.run()

    assert res.pages == 2
    assert res.origins == 1 + 1 + 1

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    assert len(scheduler_origins) == len(expected_origins)

    assert [
        (
            scheduled.visit_type,
            scheduled.url,
            scheduled.extra_loader_arguments["artifacts"],
        )
        for scheduled in sorted(scheduler_origins, key=lambda scheduled: scheduled.url)
    ] == [
        (
            "puppet",
            expected["url"],
            expected["artifacts"],
        )
        for expected in sorted(expected_origins, key=lambda expected: expected["url"])
    ]


def test_puppet_lister_incremental(datadir, requests_mock_datadir, swh_scheduler):
    # First run
    lister = PuppetLister(scheduler=swh_scheduler)
    res = lister.run()

    assert res.pages == 2
    assert res.origins == 1 + 1 + 1

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    assert len(scheduler_origins) == len(expected_origins)

    assert [
        (
            scheduled.visit_type,
            scheduled.url,
            scheduled.extra_loader_arguments["artifacts"],
        )
        for scheduled in sorted(scheduler_origins, key=lambda scheduled: scheduled.url)
    ] == [
        (
            "puppet",
            expected["url"],
            expected["artifacts"],
        )
        for expected in sorted(expected_origins, key=lambda expected: expected["url"])
    ]

    # Second run
    lister = PuppetLister(scheduler=swh_scheduler)
    # Force lister.state.last_listing_date for correct fixture loading

    lister.state.last_listing_date = datetime(2022, 9, 26, 18, 0).astimezone(
        timezone(timedelta(hours=-7))
    )
    res = lister.run()

    assert res.pages == 1
    assert res.origins == 1
