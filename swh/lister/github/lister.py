# Copyright (C) 2015  Stefano Zacchiroli <zack@upsilon.cc>
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

# see https://developer.github.com/v3/ for GitHub API documentation

import datetime
import gzip
import logging
import os
import random
import re
import requests
import time

from pprint import pformat

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from swh.core import config
from swh.lister.github.base import SWHLister
from swh.lister.github.db_utils import session_scope
from swh.lister.github.models import Repository


GH_API_URL = 'https://api.github.com'
MAX_RETRIES = 7
MAX_SLEEP = 3600  # 1 hour
CONN_SLEEP = 10

REPO_API_URL_RE = re.compile(r'^.*/repositories\?since=(\d+)')


class FetchError(RuntimeError):

    def __init__(self, response):
        self.response = response

    def __str__(self):
        return repr(self.response)


def save_http_response(r, cache_dir):
    def escape_url_path(p):
        return p.replace('/', '__')

    fname = os.path.join(cache_dir,
                         escape_url_path(r.request.path_url) + '.gz')
    with gzip.open(fname, 'w') as f:
        def emit(s):
            f.write(bytes(s, 'UTF-8'))
        emit(pformat(r.request.path_url))
        emit('\n#\n')
        emit(pformat(r.status_code))
        emit('\n#\n')
        emit(pformat(r.headers))
        emit('\n#\n')
        emit(pformat(r.json()))


def gh_api_request(path, username=None, password=None, session=None,
                   headers=None):
    params = {}

    if headers is None:
        headers = {}

    if 'Accept' not in headers:  # request version 3 of the API
        headers['Accept'] = 'application/vnd.github.v3+json'

    params['headers'] = headers
    if username is not None and password is not None:
        params['auth'] = (username, password)

    if session is None:
        session = requests.Session()

    retries_left = MAX_RETRIES
    while retries_left > 0:
        logging.debug('sending API request: %s' % path)
        try:
            r = session.get(GH_API_URL + path, **params)
        except requests.exceptions.ConnectionError:
            # network-level connection error, try again
            logging.warn('connection error upon %s: sleep for %d seconds' %
                         (path, CONN_SLEEP))
            time.sleep(CONN_SLEEP)
            retries_left -= 1
            continue

        if r.ok:  # all went well, do not retry
            break

        # detect throttling
        if r.status_code == 403 and \
           int(r.headers['X-RateLimit-Remaining']) == 0:
            delay = int(r.headers['X-RateLimit-Reset']) - time.time()
            delay = min(delay, MAX_SLEEP)
            logging.warn('rate limited upon %s: sleep for %d seconds' %
                         (path, int(delay)))
            time.sleep(delay)
        else:  # unexpected error, abort
            break

        retries_left -= 1

    if not retries_left:
        logging.warn('giving up on %s: max retries exceed' % path)

    return r


class GitHubLister(SWHLister):
    CONFIG_BASE_FILENAME = 'lister-github'
    ADDITIONAL_CONFIG = {
        'lister_db_url': ('str', 'postgresql:///lister-github'),
        'credentials': ('list[dict]', []),
        'cache_json': ('bool', False),
        'cache_dir': ('str', '~/.cache/swh/lister/github'),
    }

    def __init__(self, override_config=None):
        super().__init__()
        if override_config:
            self.config.update(override_config)

        self.config['cache_dir'] = os.path.expanduser(self.config['cache_dir'])
        if self.config['cache_json']:
            config.prepare_folders(self.config, ['cache_dir'])

        if not self.config['credentials']:
            raise ValueError('The GitHub lister needs credentials for API')

        self.db_engine = create_engine(self.config['lister_db_url'])
        self.mk_session = sessionmaker(bind=self.db_engine)

    def lookup_repo(self, repo_id, db_session=None):
        if not db_session:
            with session_scope(self.mk_session) as db_session:
                return self.lookup_repo(repo_id, db_session=db_session)

        return db_session.query(Repository) \
                         .filter(Repository.id == repo_id) \
                         .first()

    def last_repo_id(self, db_session=None):
        if not db_session:
            with session_scope(self.mk_session) as db_session:
                return self.last_repo_id(db_session=db_session)

        t = db_session.query(func.max(Repository.id)).first()

        if t is not None:
            return t[0]

    INJECT_KEYS = ['id', 'name', 'full_name', 'html_url', 'description',
                   'fork']

    def inject_repo(self, repo, db_session=None):
        if not db_session:
            with session_scope(self.mk_session) as db_session:
                return self.inject_repo(repo, db_session=db_session)

        logging.debug('injecting repo %d' % repo['id'])
        sql_repo = self.lookup_repo(repo['id'], db_session)
        if not sql_repo:
            kwargs = {k: repo[k] for k in self.INJECT_KEYS if k in repo}
            sql_repo = Repository(**kwargs)
            db_session.add(sql_repo)
        else:
            for k in self.INJECT_KEYS:
                if k in repo:
                    setattr(sql_repo, k, repo[k])
            sql_repo.last_seen = datetime.datetime.now()

        return sql_repo

    def fetch(self, min_id=None, max_id=None):
        if min_id is None:
            min_id = 1
        if max_id is None:
            max_id = float('inf')
        next_id = min_id

        do_cache = self.config['cache_json']
        cache_dir = self.config['cache_dir']

        session = requests.Session()
        db_session = self.mk_session()
        loop_count = 0
        while min_id <= next_id <= max_id:
            logging.info('listing repos starting at %d' % next_id)

            # github API ?since=... is '>' strict, not '>='
            since = next_id - 1

            cred = random.choice(self.config['credentials'])
            repos_res = gh_api_request('/repositories?since=%d' % since,
                                       session=session, **cred)

            if do_cache:
                save_http_response(repos_res, cache_dir)

            if not repos_res.ok:
                raise FetchError(repos_res)

            repos = repos_res.json()
            mapped_repos = {}
            for repo in repos:
                if repo['id'] > max_id:  # do not overstep max_id
                    break
                full_name = repo['full_name']
                mapped_repos[full_name] = self.inject_repo(repo, db_session)

            if 'next' in repos_res.links:
                next_url = repos_res.links['next']['url']
                m = REPO_API_URL_RE.match(next_url)  # parse next_id
                next_id = int(m.group(1)) + 1
            else:
                logging.info('stopping after id %d, no next link found' %
                             next_id)
                break

            loop_count += 1
            if loop_count == 20:
                logging.info('flushing updates')
                loop_count = 0
                db_session.commit()
                db_session = self.mk_session()

        db_session.commit()
