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

### Preparation steps

1. git clone under $SWH_ENVIRONMENT_HOME/swh-lister (of your choosing)
2. mkdir ~/.config/swh/ ~/.cache/swh/lister/github.com/
3. create configuration file ~/.config/swh/lister-github.com.yml
4. Bootstrap the db instance schema

    $ createdb lister-github
    $ python3 -m swh.lister.cli --db-url postgres:///lister-github \
        --lister github \
        --create-tables

### Configuration file sample

    $ cat ~/.config/swh/lister-github.com.yml
    # see http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls
    lister_db_url: postgres:///lister-github
    credentials: []
    cache_responses: True
    cache_dir: /home/zack/.cache/swh/lister/github.com
    storage:
      cls: remote
      args:
        url: http://localhost:5002/

### Run

    $ python3
    >>> import logging
    >>> logging.basicConfig(level=logging.DEBUG)
    >>> from swh.lister.github.tasks import RangeGitHubLister
    >>> RangeGitHubLister().run(364, 365)
    INFO:root:listing repos starting at 364
    DEBUG:urllib3.connectionpool:Starting new HTTPS connection (1): api.github.com
    DEBUG:urllib3.connectionpool:https://api.github.com:443 "GET /repositories?since=364 HTTP/1.1" 200 None
    DEBUG:urllib3.connectionpool:Starting new HTTP connection (1): localhost
    DEBUG:urllib3.connectionpool:http://localhost:5002 "POST /origin/add HTTP/1.1" 200 1


## lister-gitlab

### preparation steps

1. git clone under $SWH_ENVIRONMENT_HOME/swh-lister (of your choosing)
2. mkdir ~/.config/swh/ ~/.cache/swh/lister/gitlab/
3. create configuration file ~/.config/swh/lister-gitlab.yml
4. Bootstrap the db instance schema

    $ createdb lister-gitlab
    $ python3 -m swh.lister.cli --db-url postgres:///lister-gitlab \
        --lister gitlab \
        --create-tables

### Configuration file sample

    $ cat ~/.config/swh/lister-gitlab.yml
    # see http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls
    lister_db_url: postgres:///lister-gitlab
    credentials: []
    cache_responses: True
    cache_dir: /home/zack/.cache/swh/lister/gitlab
    storage:
      cls: remote
      args:
        url: http://localhost:5002/

### Run

    $ python3
    Python 3.6.6 (default, Jun 27 2018, 14:44:17)
    [GCC 8.1.0] on linux
    Type "help", "copyright", "credits" or "license" for more information.
    >>> from swh.lister.gitlab.tasks import RangeGitLabLister; RangeGitLabLister().run_task(1, 2,
    instance='salsa.debian.org', api_baseurl='https://salsa.debian.org/api/v4')
    >>> from swh.lister.gitlab.tasks import RangeGitLabLister; RangeGitLabLister().run_task(1, 2,
    instance='gitlab.freedesktop.org', api_baseurl='https://gitlab.freedesktop.org/api/v4')
    >>> from swh.lister.gitlab.tasks import RangeGitLabLister; RangeGitLabLister().run_task(1, 2,
    instance='gitlab.gnome.org', api_baseurl='https://gitlab.gnome.org/api/v4')
    >>> from swh.lister.gitlab.tasks import RangeGitLabLister; RangeGitLabLister().run_task(1, 2,
    instance='gitlab.inria.fr', api_baseurl='https://gitlab.inria.fr/api/v4')
    >>>
