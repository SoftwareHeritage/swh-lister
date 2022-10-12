# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


"""
Hackage lister
==============

The Hackage lister list origins from `hackage.haskell.org`_, the `Haskell`_ Package
Repository.

The registry provide an `http api`_ from where the lister retrieve package names
and build origins urls.

As of August 2022 `hackage.haskell.org`_ list 15536 package names.

Origins retrieving strategy
---------------------------

To get a list of all package names we make a POST call to
``https://hackage.haskell.org/packages/search`` endpoint with some params given as
json data.

Default params::

    {
        "page": 0,
        "sortColumn": "default",
        "sortDirection": "ascending",
        "searchQuery": "(deprecated:any)",
    }

The page size is 50. The lister will make has much http api call has needed to get
all results.

For incremental mode we expand the search query with ``lastUpload`` greater than
``state.last_listing_date``, the api will return all new or updated package names since
last run.

Page listing
------------

The result is paginated, each page is 50 records long.

Entry data set example::

    {
        "description": "3D model parsers",
        "downloads": 6,
        "lastUpload": "2014-11-08T03:55:23.879047Z",
        "maintainers": [{"display": "capsjac", "uri": "/user/capsjac"}],
        "name": {"display": "3dmodels", "uri": "/package/3dmodels"},
        "tags": [
            {"display": "graphics", "uri": "/packages/tag/graphics"},
            {"display": "lgpl", "uri": "/packages/tag/lgpl"},
            {"display": "library", "uri": "/packages/tag/library"},
        ],
        "votes": 1.5,
    }

Origins from page
-----------------

The lister yields 50 origins url per page.
Each ListedOrigin has a ``last_update`` date set.

Running tests
-------------

Activate the virtualenv and run from within swh-lister directory::

   pytest -s -vv --log-cli-level=DEBUG swh/lister/hackage/tests

Testing with Docker
-------------------

Change directory to swh/docker then launch the docker environment::

   docker compose up -d

Then schedule an Hackage listing task::

   docker compose exec swh-scheduler swh scheduler task add -p oneshot list-hackage

You can follow lister execution by displaying logs of swh-lister service::

   docker compose logs -f swh-lister

.. _hackage.haskell.org: https://hackage.haskell.org/
.. _Haskell: https://haskell.org/
.. _http api: https://hackage.haskell.org/api
"""


def register():
    from .lister import HackageLister

    return {
        "lister": HackageLister,
        "task_modules": ["%s.tasks" % __name__],
    }
