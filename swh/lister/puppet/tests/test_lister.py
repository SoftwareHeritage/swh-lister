# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information
from swh.lister.puppet.lister import PuppetLister

expected_origins = {
    "https://forge.puppet.com/modules/electrical/file_concat": {
        "artifacts": {
            "1.0.0": {
                "url": "https://forgeapi.puppet.com/v3/files/electrical-file_concat-1.0.0.tar.gz",  # noqa: B950
                "version": "1.0.0",
                "filename": "electrical-file_concat-1.0.0.tar.gz",
                "last_update": "2015-04-09T12:03:13-07:00",
            },
            "1.0.1": {
                "url": "https://forgeapi.puppet.com/v3/files/electrical-file_concat-1.0.1.tar.gz",  # noqa: B950
                "version": "1.0.1",
                "filename": "electrical-file_concat-1.0.1.tar.gz",
                "last_update": "2015-04-17T01:03:46-07:00",
            },
        }
    },
    "https://forge.puppet.com/modules/puppetlabs/puppetdb": {
        "artifacts": {
            "1.0.0": {
                "url": "https://forgeapi.puppet.com/v3/files/puppetlabs-puppetdb-1.0.0.tar.gz",  # noqa: B950
                "version": "1.0.0",
                "filename": "puppetlabs-puppetdb-1.0.0.tar.gz",
                "last_update": "2012-09-19T16:51:22-07:00",
            },
            "7.9.0": {
                "url": "https://forgeapi.puppet.com/v3/files/puppetlabs-puppetdb-7.9.0.tar.gz",  # noqa: B950
                "version": "7.9.0",
                "filename": "puppetlabs-puppetdb-7.9.0.tar.gz",
                "last_update": "2021-06-24T07:48:54-07:00",
            },
            "7.10.0": {
                "url": "https://forgeapi.puppet.com/v3/files/puppetlabs-puppetdb-7.10.0.tar.gz",  # noqa: B950
                "version": "7.10.0",
                "filename": "puppetlabs-puppetdb-7.10.0.tar.gz",
                "last_update": "2021-12-16T14:57:46-08:00",
            },
        }
    },
    "https://forge.puppet.com/modules/saz/memcached": {
        "artifacts": {
            "1.0.0": {
                "url": "https://forgeapi.puppet.com/v3/files/saz-memcached-1.0.0.tar.gz",  # noqa: B950
                "version": "1.0.0",
                "filename": "saz-memcached-1.0.0.tar.gz",
                "last_update": "2011-11-20T13:40:30-08:00",
            },
            "8.1.0": {
                "url": "https://forgeapi.puppet.com/v3/files/saz-memcached-8.1.0.tar.gz",  # noqa: B950
                "version": "8.1.0",
                "filename": "saz-memcached-8.1.0.tar.gz",
                "last_update": "2022-07-11T03:34:55-07:00",
            },
        }
    },
}


def test_puppet_lister(datadir, requests_mock_datadir, swh_scheduler):
    lister = PuppetLister(scheduler=swh_scheduler)
    res = lister.run()

    assert res.pages == 2
    assert res.origins == 1 + 1 + 1

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    assert len(scheduler_origins) == len(expected_origins)

    for origin in scheduler_origins:
        assert origin.visit_type == "puppet"
        assert origin.url in expected_origins
        assert origin.extra_loader_arguments == expected_origins[origin.url]
