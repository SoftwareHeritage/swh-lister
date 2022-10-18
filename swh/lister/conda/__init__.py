# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


"""
Conda lister
============

Anaconda is a package manager that provides tooling for datascience.

The Conda lister list `packages`_ from Anaconda `repositories`_.
Those repositories host packages for several languages (Python, R) operating systems
and architecture.
Packages are grouped within free or commercial `channels`_.

To instantiate a conda lister we need to give some `channel`and `arch` arguments::

    lister = CondaLister(
        scheduler=swh_scheduler, channel="free", archs=["linux-64", "osx-64", "win-64"]
    )

The default `url` value of lister is `https://repo.anaconda.com/pkgs`. One can set another
repository url, for example::

    lister = CondaLister(
        scheduler=swh_scheduler,
        url="https://conda.anaconda.org",
        channel="conda-forge",
        archs=["linux-64"],
    )

Origins retrieving strategy
---------------------------

Each channel provides several `repodata.json`_ files that list available packages
and related versions.

Given a channel and a list of system and architecture the lister download and parse
corresponding repodata.json.

We use bz2 compressed version of repodata.json. See for example `main/linux-64`_ page
to view available repodata files.

Page listing
------------

The lister returns one page per channel / architecture that list all available package
versions.

Origins from page
-----------------

Origins urls are built following this pattern `https://anaconda.org/{channel}/{pkgname}`.
Each origin is yield with an `artifacts` entry in `extra_loader_arguments` that list
artifact metadata for each archived package version.

Origin data example for one origin with two related versions.::

    {
        "url": "https://anaconda.org/conda-forge/lifetimes",
        "artifacts": {
            "linux-64/0.11.1-py36h9f0ad1d_1": {
                "url": "https://conda.anaconda.org/conda-forge/linux-64/lifetimes-0.11.1-py36h9f0ad1d_1.tar.bz2",  # noqa: B950
                "date": "2020-07-06T12:19:36.425000+00:00",
                "version": "0.11.1",
                "filename": "lifetimes-0.11.1-py36h9f0ad1d_1.tar.bz2",
                "checksums": {
                    "md5": "faa398f7ba0d60ce44aa6eeded490cee",
                    "sha256": "f82a352dfae8abceeeaa538b220fd9c5e4aa4e59092a6a6cea70b9ec0581ea03",  # noqa: B950
                },
            },
            "linux-64/0.11.1-py36hc560c46_1": {
                "url": "https://conda.anaconda.org/conda-forge/linux-64/lifetimes-0.11.1-py36hc560c46_1.tar.bz2",  # noqa: B950
                "date": "2020-07-06T12:19:37.032000+00:00",
                "version": "0.11.1",
                "filename": "lifetimes-0.11.1-py36hc560c46_1.tar.bz2",
                "checksums": {
                    "md5": "c53a689a4c5948e84211bdfc23e3fe68",
                    "sha256": "76146c2ebd6e3b65928bde53a2585287759d77beba785c0eeb889ee565c0035d",  # noqa: B950
                },
            },
        },
    }

Running tests
-------------

Activate the virtualenv and run from within swh-lister directory::

   pytest -s -vv --log-cli-level=DEBUG swh/lister/conda/tests

Testing with Docker
-------------------

Change directory to swh/docker then launch the docker environment::

   docker compose up -d

Then schedule a conda listing task::

   docker compose exec swh-scheduler swh scheduler task add -p oneshot list-conda channel="free" archs="[linux-64, osx-64, win-64]"  # noqa: B950

You can follow lister execution by displaying logs of swh-lister service::

   docker compose logs -f swh-lister

.. _packages: https://docs.anaconda.com/anaconda/packages/pkg-docs/
.. _Anaconda: https://anaconda.com/
.. _repositories: https://repo.anaconda.com/pkgs/
.. _channels: https://docs.anaconda.com/anaconda/user-guide/tasks/using-repositories/
.. _main/linux-64: https://repo.anaconda.com/pkgs/main/linux-64/
.. _repodata.json: https://repo.anaconda.com/pkgs/free/linux-64/repodata.json
"""


def register():
    from .lister import CondaLister

    return {
        "lister": CondaLister,
        "task_modules": ["%s.tasks" % __name__],
    }
