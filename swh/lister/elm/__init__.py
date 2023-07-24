# Copyright (C) 2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


"""
Elm lister
==========

`Elm`_ is a functional language that compiles to JavaScript.

Additional packages for the language can be searched from the `Packages`_ website
and installed with `elm install`_ command. The Elm packages website also provides a
`Http Api endpoint`_ listing all available packages.

Elm origins are Git repositories hosted on Github. Each repository must provide its
packaged releases using the Github release system.

As of July 2023 `Packages`_ list 1746 packages.

Origins retrieving strategy
---------------------------

To build a list of origins we make a GET request to the `Http Api endpoint`_ that returns
a Json array of objects.
The origin url for each package is constructed with the information of corresponding
`name` entry which represents the suffix of Github repositories (org/project_name).

Page listing
------------

There is only one page listing all origins url.

Origins from page
-----------------

The lister is stateless and yields all origins url from one page. It is a list of package
repository url.

Running tests
-------------

Activate the virtualenv and run from within swh-lister directory::

   pytest -s -vv --log-cli-level=DEBUG swh/lister/elm/tests

Testing with Docker
-------------------

Change directory to swh/docker then launch the docker environment::

   docker compose up -d

Then schedule a elm listing task::

   docker compose exec swh-scheduler swh scheduler task add -p oneshot list-elm

You can follow lister execution by displaying logs of swh-lister service::

   docker compose logs -f swh-lister

.. _Elm: https://elm-lang.org/
.. _Packages: https://package.elm-lang.org/
.. _elm install: https://guide.elm-lang.org/install/elm.html#elm-install
.. _Http Api endpoint: https://package.elm-lang.org/search.json
"""


def register():
    from .lister import ElmLister

    return {
        "lister": ElmLister,
        "task_modules": ["%s.tasks" % __name__],
    }
