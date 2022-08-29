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

To get a list of all package names we call `https://pub.dev/api/packages` endpoint.
There is no other way for discovery (no archive index, no database dump, no dvcs repository).

Page listing
------------

There is only one page that list all origins url based
on `https://pub.dev/api/packages/{pkgname}`.
The origin url corresponds to the http api endpoint that returns complete information
about the package versions (name, version, author, description, release date).

Origins from page
-----------------

The lister yields all origins url from one page.

Running tests
-------------

Activate the virtualenv and run from within swh-lister directory::

   pytest -s -vv --log-cli-level=DEBUG swh/lister/pubdev/tests

Testing with Docker
-------------------

Change directory to swh/docker then launch the docker environment::

   docker-compose up -d

Then connect to the lister::

   docker exec -it docker_swh-lister_1 bash

And run the lister (The output of this listing results in “oneshot” tasks in the scheduler)::

   swh lister run -l pubdev

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