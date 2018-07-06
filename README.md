SWH-lister
============

The Software Heritage Lister is both a library module to permit to
centralize lister behaviors, and to provide lister implementations.

Actual lister implementations are:

- swh-lister-debian
- swh-lister-github
- swh-lister-bitbucket

Licensing
----------

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

See top-level LICENSE file for the full text of the GNU General Public License
along with this program.


Dependencies
------------

- python3
- python3-requests
- python3-sqlalchemy

More details in requirements*.txt


Local deployment
-----------

## lister-github

1. git clone under $GHLISTER_ROOT (of your choosing)
2. mkdir ~/.config/swh/ ~/.cache/swh/lister/github.com/
3. create configuration file ~/.config/swh/lister-github.com.yml
4. Bootstrap the db instance schema

    $ createdb lister-github
    $ python3 -m swh.lister.cli --db-url postgres:///lister-github \
        --lister github \
        --create-tables


Configuration file samples
-------------------------

## github

cat ~/.config/swh/lister-github.com.yml

    # see http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls
    lister_db_url: postgres:///lister-github.com
    credentials: []
    cache_responses: True
    cache_dir: /home/zack/.cache/swh/lister/github.com

    storage:
      cls: remote
      args:
        url: http://localhost:5002/
