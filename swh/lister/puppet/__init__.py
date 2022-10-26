# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


"""
Puppet lister
=============

The Puppet lister list origins from `Puppet Forge`_.
Puppet Forge is a package manager for Puppet modules.

As of September 2022 `Puppet Forge`_ list 6917 package names.

Origins retrieving strategy
---------------------------

To get a list of all package names we call an `http api endpoint`_  which have a
`getModules`_ endpoint.
It returns a paginated list of results and a `next` url.

The api follow `OpenApi 3.0 specifications`.

The lister is incremental using ``with_release_since`` api argument whose value is an
iso date set regarding the last time the lister has been executed, stored as
``lister.state.last_listing_date``.

Page listing
------------

Each page returns a list of ``results`` which are raw data from api response.
The results size is 100 as 100 is the maximum limit size allowed by the api.

Origins from page
-----------------

The lister yields one hundred origin url per page.

Origin url is the html page corresponding to a package name on the forge, following
this pattern::

    "https://forge.puppet.com/modules/{owner}/{pkgname}"

For each origin `last_update` is set via the module "updated_at" value.
As the api also returns all existing versions for a package, we build an `artifacts`
dict in `extra_loader_arguments` with the archive tarball corresponding to each
existing versions.

Example for ``file_concat`` module located at
https://forge.puppet.com/modules/electrical/file_concat::

    {
        "artifacts": [
            {
                "url": "https://forgeapi.puppet.com/v3/files/electrical-file_concat-1.0.1.tar.gz",  # noqa: B950
                "version": "1.0.1",
                "filename": "electrical-file_concat-1.0.1.tar.gz",
                "last_update": "2015-04-17T01:03:46-07:00",
                "checksums": {
                    "md5": "74901a89544134478c2dfde5efbb7f14",
                    "sha256": "15e973613ea038d8a4f60bafe2d678f88f53f3624c02df3157c0043f4a400de6",  # noqa: B950
                },
            },
            {
                "url": "https://forgeapi.puppet.com/v3/files/electrical-file_concat-1.0.0.tar.gz",  # noqa: B950
                "version": "1.0.0",
                "filename": "electrical-file_concat-1.0.0.tar.gz",
                "last_update": "2015-04-09T12:03:13-07:00",
                "checksums": {
                    "length": 13289,
                },
            },
        ],
    }

Running tests
-------------

Activate the virtualenv and run from within swh-lister directory::

   pytest -s -vv --log-cli-level=DEBUG swh/lister/puppet/tests

Testing with Docker
-------------------

Change directory to swh/docker then launch the docker environment::

   docker compose up -d

Then schedule a Puppet listing task::

   docker compose exec swh-scheduler swh scheduler task add -p oneshot list-puppet

You can follow lister execution by displaying logs of swh-lister service::

   docker compose logs -f swh-lister

.. _Puppet Forge: https://forge.puppet.com/
.. _http api endpoint: https://forgeapi.puppet.com/
.. _getModules: https://forgeapi.puppet.com/#tag/Module-Operations/operation/getModules

"""


def register():
    from .lister import PuppetLister

    return {
        "lister": PuppetLister,
        "task_modules": ["%s.tasks" % __name__],
    }
