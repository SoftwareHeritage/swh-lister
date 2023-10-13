# Copyright (C) 2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


"""
Julia lister
=============

`Julia`_ is a dynamic language for scientific computing applications. It comes with
an ecosystem of packages managed with its internal package manager `Pkg`_.

A list of all officially registered packages can be found in the `Julia General Registry`_
on GitHub, but it's easier to search for packages using the `JuliaHub`_ and
`Julia Packages`_ sites.

The `Julia`_ lister lists origins from a Git repository, the `Julia General registry`_.
The main `Registry.toml`_ file list available Julia packages. Each directory
match a package name and have Toml files to describe the package and its versions.

Julia origins are Git repositories hosted on Github. Each repository must provide its
packaged releases using the Github release system.

As of July 2023 `Julia General registry`_ list 9714 packages names.

Origins retrieval strategy
--------------------------

To build a list of origins we clone the `Julia General registry`_ Git repository, then
walk through commits with the help of `Dulwich`_ to detect commit related to a new package
or a new version of a package. For each of those commits we get the path to `Package.toml`
file from where we get the Git repository url for a package.

Page listing
------------

There is only one page listing all origins url.

Origins from page
-----------------

The lister yields all origins url from one page.

Each time the lister is executed, the HEAD commit id of `Julia General registry`_
is stored as ``state.last_seen_commit`` and used on next run to retrieve new origins
since the last commit.

Each url corresponds to the Git url of the package repository.

Running tests
-------------

Activate the virtualenv and run from within swh-lister directory::

   pytest -s -vv --log-cli-level=DEBUG swh/lister/julia/tests

Testing with Docker
-------------------

Change directory to swh/docker then launch the docker environment::

   docker compose up -d

Then schedule a julia listing task::

   docker compose exec swh-scheduler swh scheduler task add -p oneshot list-julia

You can follow lister execution by displaying logs of swh-lister service::

   docker compose logs -f swh-lister

.. _Julia: https://julialang.org/
.. _Pkg: https://docs.julialang.org/en/v1/stdlib/Pkg/
.. _Julia General registry: https://github.com/JuliaRegistries/General
.. _JuliaHub: https://juliahub.com/
.. _Julia Packages: https://julialang.org/packages/
.. _Registry.toml: https://github.com/JuliaRegistries/General/blob/master/Registry.toml
.. _Dulwich: https://www.dulwich.io/
"""  # noqa: B950


def register():
    from .lister import JuliaLister

    return {
        "lister": JuliaLister,
        "task_modules": ["%s.tasks" % __name__],
    }
