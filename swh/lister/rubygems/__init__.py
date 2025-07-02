# Copyright (C) 2022-2025  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


"""
RubyGems lister
===============

The RubyGems lister list origins from `RubyGems.org`_, the Ruby community's gem hosting service.

As of July 2025 `RubyGems.org`_ list 186,003 package names.

Origins retrieving strategy
---------------------------

To list all available gems and retrieve relevant data about gems in a performant way, the daily
`PostgreSQL database dump`_ of RubyGems, is exploited.

All gems are listed by executing the following query:

.. code-block:: sql

   SELECT id, name FROM rubygems

Relevant listing data are then retrieved by executing that query for each gem:

.. code-block:: sql

   SELECT built_at, full_name, number, sha256, size
   FROM versions
   WHERE rubygem_id = <gem_id> AND yanked_at IS NULL

Page listing
------------

Each page returns listing info about one gem, its origin url is based on the following pattern::

    https://rubygems.org/gems/{gem_name}

Origins from page
-----------------

The lister yields one listed origin per page.

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
.. _PostgreSQL database dump: https://rubygems.org/pages/data
"""


def register():
    from .lister import RubyGemsLister

    return {
        "lister": RubyGemsLister,
        "task_modules": ["%s.tasks" % __name__],
    }
