# Copyright (C) 2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


"""
Dlang lister
=============

D is a general-purpose programming language with static typing, systems-level access,
and C-like syntax.

The `Dlang`_ lister list origins from its packages manager registry `DUB`_.

The registry provides an `http api endpoint`_ that helps in getting the packages index
with name, url, versions and dates.

As of July 2023 `DUB`_ list 2364 package names.

Origins retrieving strategy
---------------------------

To build a list of origins we make a GET request to an `http api endpoint`_ that returns
a JSON-formatted array of objects.
The origin url for each package is constructed with the information of corresponding
`repository` entry which represents Git based projects hosted on Github, GitLab or
Bitbucket.

Page listing
------------

There is only one page listing all origins url.

Origins from page
-----------------

The lister is stateless and yields all origins url from one page. It is a list of package
url with last update information.

Running tests
-------------

Activate the virtualenv and run from within swh-lister directory::

   pytest -s -vv --log-cli-level=DEBUG swh/lister/dlang/tests

Testing with Docker
-------------------

Change directory to swh/docker then launch the docker environment::

   docker compose up -d

Then schedule a dlang listing task::

   docker compose exec swh-scheduler swh scheduler task add -p oneshot list-dlang

You can follow lister execution by displaying logs of swh-lister service::

   docker compose logs -f swh-lister

.. _Dlang: https://dlang.org/
.. _DUB: https://code.dlang.org/
.. _http api endpoint: https://code.dlang.org/api/packages/dump"
"""


def register():
    from .lister import DlangLister

    return {
        "lister": DlangLister,
        "task_modules": ["%s.tasks" % __name__],
    }
