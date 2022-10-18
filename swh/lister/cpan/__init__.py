# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


"""
Cpan lister
=============

The Cpan lister list origins from `cpan.org`_, the Comprehensive Perl Archive
Network. It provides search features via `metacpan.org`_.

As of September 2022 `cpan.org`_ list 43675 package names.

Origins retrieving strategy
---------------------------

To get a list of all package names and their associated release artifacts we call
a first `http api endpoint`_ that retrieve results and a ``_scroll_id`` that will
be used to scroll pages through `search`_ endpoint.

Page listing
------------

Each page returns a list of ``results`` which are raw data from api response.

Origins from page
-----------------

Origin url is the html page corresponding to a package name on `metacpan.org`_, following
this pattern::

    "https://metacpan.org/dist/{pkgname}"

Running tests
-------------

Activate the virtualenv and run from within swh-lister directory::

   pytest -s -vv --log-cli-level=DEBUG swh/lister/cpan/tests

Testing with Docker
-------------------

Change directory to swh/docker then launch the docker environment::

   docker compose up -d

Then schedule a Cpan listing task::

   docker compose exec swh-scheduler swh scheduler task add -p oneshot list-cpan

You can follow lister execution by displaying logs of swh-lister service::

   docker compose logs -f swh-lister

.. _cpan.org: https://cpan.org/
.. _metacpan.org: https://metacpan.org/
.. _http api endpoint: https://explorer.metacpan.org/?url=/release/
.. _search: https://github.com/metacpan/metacpan-api/blob/master/docs/API-docs.md#search-without-constraints  # noqa: B950


"""


def register():
    from .lister import CpanLister

    return {
        "lister": CpanLister,
        "task_modules": ["%s.tasks" % __name__],
    }
