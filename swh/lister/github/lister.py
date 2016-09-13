# Copyright (C) 2015  Stefano Zacchiroli <zack@upsilon.cc>
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

# see https://developer.github.com/v3/ for GitHub API documentation

import gzip
import logging
import os
import re
import requests
import time

from pprint import pformat
from sqlalchemy import func

from swh.lister.github.db_utils import session_scope
from swh.lister.github.models import Repository


GH_API_URL = 'https://api.github.com'
MAX_RETRIES = 7
MAX_SLEEP = 3600  # 1 hour
CONN_SLEEP = 10

REPO_API_URL_RE = re.compile(r'^.*/repositories\?since=(\d+)')


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


def gh_api_request(path, username=None, password=None, headers={}):
    params = {}
    if 'Accept' not in headers:  # request version 3 of the API
        headers['Accept'] = 'application/vnd.github.v3+json'
    params['headers'] = headers
    if username is not None and password is not None:
        params['auth'] = (username, password)

    retries_left = MAX_RETRIES
    while retries_left > 0:
        logging.debug('sending API request: %s' % path)
        try:
            r = requests.get(GH_API_URL + path, **params)
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


def lookup_repo(db_session, repo_id):
    return db_session.query(Repository) \
                     .filter(Repository.id == repo_id) \
                     .first()


def last_repo_id(db_session):
    t = db_session.query(func.max(Repository.id)) \
                  .first()
    if t is not None:
        return t[0]
    # else: return None


INJECT_KEYS = ['id', 'name', 'full_name', 'html_url', 'description', 'fork']


def inject_repo(db_session, repo):
    logging.debug('injecting repo %d' % repo['id'])
    if lookup_repo(db_session, repo['id']):
        logging.info('not injecting already present repo %d' % repo['id'])
        return
    kwargs = {k: repo[k] for k in INJECT_KEYS if k in repo}
    sql_repo = Repository(**kwargs)
    db_session.add(sql_repo)


class FetchError(RuntimeError):

    def __init__(self, response):
        self.response = response

    def __str__(self):
        return repr(self.response)


def fetch(conf, mk_session, min_id=None, max_id=None):
    if min_id is None:
        min_id = 1
    if max_id is None:
        max_id = float('inf')
    next_id = min_id

    cred = {}
    for key in ['username', 'password']:
        if key in conf:
            cred[key] = conf[key]

    while min_id <= next_id <= max_id:
        logging.info('listing repos starting at %d' % next_id)
        since = next_id - 1  # github API ?since=... is '>' strict, not '>='
        repos_res = gh_api_request('/repositories?since=%d' % since, **cred)

        if 'cache_dir' in conf and conf['cache_json']:
            save_http_response(repos_res, conf['cache_dir'])
        if not repos_res.ok:
            raise FetchError(repos_res)

        repos = repos_res.json()
        for repo in repos:
            if repo['id'] > max_id:  # do not overstep max_id
                break
            with session_scope(mk_session) as db_session:
                inject_repo(db_session, repo)

        if 'next' in repos_res.links:
            next_url = repos_res.links['next']['url']
            m = REPO_API_URL_RE.match(next_url)  # parse next_id
            next_id = int(m.group(1)) + 1
        else:
            logging.info('stopping after id %d, no next link found' % next_id)
            break
