swh-lister
============

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
- python3-psycopg2
- python3-requests
- python3-sqlalchemy


Deployment
-----------

1. git clone under $GHLISTER_ROOT (of your choosing)
2. mkdir ~/.config/swh/ ~/.cache/swh/lister-github/
3. edit $GHLISTER_ROOT/etc/crontab and customize GHLISTER_ROOT
4. crontab $GHLISTER_ROOT/etc/crontab
5. create configuration file ~/.config/swh/lister-github.ini

Sample configuration file
-------------------------

cat ~/.config/swh/lister-github.ini

        [main]
        db_url = postgres:///github
          # see http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls
        cache_dir = /home/zack/.cache/swh/lister-github
        log_dir =   /home/zack/.cache/swh/lister-github
        username = foobar  # github username
        password = quux    # github password
