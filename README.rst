Software Heritage - Listers
===========================

Collection of listers for source code distribution places like development
forges, FOSS distributions, package managers, etc. Each lister is in charge to
enumerate the software origins (e.g., VCS, packages, etc.) available at a
source code distribution place.

A lister is a component from the Software Heritage stack aims to produce
listings of software origins and their urls hosted on various public developer
platforms or package managers. As these operations are quite similar, this
package provides a set of Python modules abstracting common software origins
listing behaviors.

It also provides several lister implementations, contained in the Python
``swh.lister.*`` modules. See `this documentation
<https://docs.softwareheritage.org/user/listers.html>`_ for the list of
supported listers.


Dependencies
------------

All required python dependencies can be found in the ``requirements*.txt`` files
located at the root of the repository.

In order to be able to run all the listers (and thus execute the tests), some
tools must be available on your system, namely:

- ``opam``
- ``tar``
- ``psql``

On a Debian-like system, you may use:

.. code-block: console

   $ sudo apt update
   $ sudo apt install opam tar postgresql-client-common


Local deployment
----------------

Lister configuration
++++++++++++++++++++

Each lister implemented so far by Software Heritage (``bitbucket``, ``cgit``,
``cran``, ``debian``, ``gitea``, ``github``, ``gitlab``, ``gnu``, ``golang``,
``launchpad``, ``npm``, ``packagist``, ``phabricator``, ``pypi``, ``tuleap``,
``maven``) must be configured by following the instructions below (please note
that you have to replace ``<lister_name>`` by one of the lister name introduced
above).

Preparation steps
~~~~~~~~~~~~~~~~~

1. ``mkdir ~/.config/swh/``
2. create configuration file ``~/.config/swh/listers.yml``

Configuration file sample
+++++++++++++++++++++++++

Minimalistic configuration shared by all listers to add in file
``~/.config/swh/listers.yml``:

.. code-block:: yaml

   scheduler:
     cls: 'remote'
     args:
       url: 'http://localhost:5008/'

   credentials: {}

Note: This expects scheduler (5008) service to run locally

Executing a lister
------------------

Once configured, a lister can be executed by using the ``swh`` CLI tool with
the following options and commands:

.. code-block:: shell

   $ swh --log-level DEBUG lister -C ~/.config/swh/listers.yml run --lister <lister_name> [lister_parameters]


Examples:

.. code-block:: shell

   $ swh --log-level DEBUG lister -C ~/.config/swh/listers.yml run --lister bitbucket

   $ swh --log-level DEBUG lister -C ~/.config/swh/listers.yml run --lister cran

   $ swh --log-level DEBUG lister -C ~/.config/swh/listers.yml run --lister gitea url=https://codeberg.org/api/v1/

   $ swh --log-level DEBUG lister -C ~/.config/swh/listers.yml run --lister gitlab url=https://salsa.debian.org/api/v4/

   $ swh --log-level DEBUG lister -C ~/.config/swh/listers.yml run --lister npm

   $ swh --log-level DEBUG lister -C ~/.config/swh/listers.yml run --lister pypi


Licensing
---------

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

See top-level LICENSE file for the full text of the GNU General Public License
along with this program.
