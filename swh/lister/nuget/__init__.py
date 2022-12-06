# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


"""
NuGet lister
============

The NuGet lister discover origins from `nuget.org`_, NuGet is the package manager for .NET.
As .NET packages mostly contains binaries, we keep only track of packages that have
a Dvcs repository (GIT, SVN, Mercurial...) url usable as an origin.

The `nuget.org/packages`_ list 301,206 packages as of September 2022.

Origins retrieving strategy
---------------------------

Nuget.org provides an `http api`_ with several endpoint to discover and list packages
and versions.

The recommended way to `retrieve all packages`_ is to use the `catalog`_ api endpoint.
It provides a `catalog index endpoint`_ that list all available pages. We then iterate to
get content of related pages.

The lister is incremental following a `cursor`_ principle, based on the value of
``commitTimeStamp`` from the catalog index endpoint. It retrieve only pages for which
``commitTimeStamp``is greater than ``lister.state.last_listing_date``.

Page listing
------------

Each page returns a list of packages which is the data of the response request.

Origins from page
-----------------

For each entry in a page listing we get related metadata through its `package metadata`_
http api endpoint. It returns uri for linked archives that contains binary, not the
original source code. Our strategy is then to get a related GIT repository.

We use another endpoint for each package to get its `package manifest`_, a .nuspec file (xml
 data) which may contains a GIT repository url. If we found one, it is used as origin.

Running tests
-------------

Activate the virtualenv and run from within swh-lister directory::

   pytest -s -vv --log-cli-level=DEBUG swh/lister/nuget/tests

Testing with Docker
-------------------

Change directory to swh/docker then launch the docker environment::

   docker compose up -d

Then schedule a nuget listing task::

   docker compose exec swh-scheduler swh scheduler task add -p oneshot list-nuget

You can follow lister execution by displaying logs of swh-lister service::

   docker compose logs -f swh-lister

.. _nuget.org: https://nuget.org
.. _nuget.org/packages: https://www.nuget.org/packages
.. _http api: https://api.nuget.org/v3/index.json
.. _catalog: https://learn.microsoft.com/en-us/nuget/api/catalog-resource
.. _catalog index endpoint: https://learn.microsoft.com/en-us/nuget/api/catalog-resource#catalog-page-object-in-the-index
.. _retrieve all packages: https://learn.microsoft.com/en-us/nuget/guides/api/query-for-all-published-packages#initialize-a-cursor
.. _cursor: https://learn.microsoft.com/en-us/nuget/api/catalog-resource#cursor
.. _package metadata: https://learn.microsoft.com/en-us/nuget/api/registration-base-url-resource
.. _package manifest: https://learn.microsoft.com/en-us/nuget/api/package-base-address-resource#download-package-manifest-nuspec
"""  # noqa: B950


def register():
    from .lister import NugetLister

    return {
        "lister": NugetLister,
        "task_modules": ["%s.tasks" % __name__],
    }
