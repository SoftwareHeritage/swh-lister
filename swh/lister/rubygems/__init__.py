# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


"""
RubyGems lister
===============

The RubyGems lister list origins from `RubyGems.org`_, the Ruby community’s gem hosting service.

As of September 2022 `RubyGems.org`_ list 173384 package names.

Origins retrieving strategy
---------------------------

To get a list of all package names we call an `http endpoint`_ which returns a list of gems
as text.

Page listing
------------

Each page returns an origin url based on the following pattern::

    https://rubygems.org/gems/{pkgname}

Origins from page
-----------------

The lister yields one origin url per page.

Running tests
-------------

Activate the virtualenv and run from within swh-lister directory::

   pytest -s -vv --log-cli-level=DEBUG swh/lister/rubygems/tests

Testing with Docker
-------------------

Change directory to swh/docker then launch the docker environment::

   docker compose up -d

Then schedule a RubyGems listing task::

   docker compose exec swh-scheduler swh scheduler task add -p oneshot list-rubygems

You can follow lister execution by displaying logs of swh-lister service::

   docker compose logs -f swh-lister

.. _RubyGems.org: https://rubygems.org/
.. _http endpoint: https://rubygems.org/versions
"""


def register():
    from .lister import RubyGemsLister

    return {
        "lister": RubyGemsLister,
        "task_modules": ["%s.tasks" % __name__],
    }
