# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


"""
Bower lister
============

The `Bower`_ lister list origins from its packages registry `registry.bower.io`_.

Bower is a tool to manage Javascript packages.

The registry provide an `http api`_ from where the lister retrieve package names
and url.

As of August 2022 `registry.bower.io`_ list 71028 package names.

Note that even if the project is still maintained(security fixes, no new features), it is
recommended to not use it anymore and prefer Yarn as a replacement since 2018.

Origins retrieving strategy
---------------------------

To get a list of all package names we call `https://registry.bower.io/packages` endpoint.
There is no other way for discovery (no archive index, no database dump, no dvcs repository).

Page listing
------------

There is only one page that list all origins url.

Origins from page
-----------------

The lister yields all origins url from one page. It is a list of package name and url.
Origins url corresponds to Git repository url.
Bower is supposed to support Svn repository too but on +/- 71000 urls I have only found 35
urls that may not be Git repository.

Running tests
-------------

Activate the virtualenv and run from within swh-lister directory::

   pytest -s -vv --log-cli-level=DEBUG swh/lister/bower/tests

Testing with Docker
-------------------

Change directory to swh/docker then launch the docker environment::

   docker compose up -d

Then schedule a bower listing task::

   docker compose exec swh-scheduler swh scheduler task add -p oneshot list-bower

You can follow lister execution by displaying logs of swh-lister service::

   docker compose logs -f swh-lister

.. _Bower: https://bower.io
.. _registry.bower.io: https://registry.bower.io
.. _http api: https://registry.bower.io/packages
"""


def register():
    from .lister import BowerLister

    return {
        "lister": BowerLister,
        "task_modules": ["%s.tasks" % __name__],
    }
