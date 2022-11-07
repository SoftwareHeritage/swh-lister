# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


"""
Pub.dev lister
==============

The Pubdev lister list origins from `pub.dev`_, the `Dart`_ and `Flutter`_ packages registry.

The registry provide an `http api`_ from where the lister retrieve package names.

As of August 2022 `pub.dev`_ list 33535 package names.

Origins retrieving strategy
---------------------------

To get a list of all package names we call `https://pub.dev/api/package-names` endpoint.
There is no other way for discovery (no archive index, no database dump, no dvcs repository).

Origins from page
-----------------

The lister yields all origin urls from a single page.

Getting last update date for each package
-----------------------------------------

Before sending a listed pubdev origin to the scheduler, we query the
`https://pub.dev/api/packages/{pkgname}` endpoint to get the last update date
for a package (date of its latest release). It enables Software Heritage to create
new loading task for a package only if it has new releases since last visit.

Running tests
-------------

Activate the virtualenv and run from within swh-lister directory::

   pytest -s -vv --log-cli-level=DEBUG swh/lister/pubdev/tests

Testing with Docker
-------------------

Change directory to swh/docker then launch the docker environment::

   docker-compose up -d

Then schedule a pubdev listing task::

   docker compose exec swh-scheduler swh scheduler task add -p oneshot list-pubdev

You can follow lister execution by displaying logs of swh-lister service::

   docker compose logs -f swh-lister

.. _pub.dev: https://pub.dev
.. _Dart: https://dart.dev
.. _Flutter: https://flutter.dev
.. _http api: https://pub.dev/help/api
"""


def register():
    from .lister import PubDevLister

    return {
        "lister": PubDevLister,
        "task_modules": ["%s.tasks" % __name__],
    }
