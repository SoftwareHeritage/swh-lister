# Copyright © 2016 The Software Heritage Developers <swh-devel@inria.fr>
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

# see https://developer.github.com/v3/ for the GitHub API documentation

import time
from urllib.parse import urljoin

import requests


GITHUB_API_BASE = 'https://api.github.com/'


def github_api_request(url, last_modified=None, etag=None, session=None,
                       credentials=None):
    """Make a request to the GitHub API at 'url'.

    Args:
        url: the URL of the GitHub API endpoint to request
        last_modified: the last time that URL was requested
        etag: the etag for the last answer at this URL (overrides
              last_modified)
        session: a requests session
        credentials: a list of dicts for GitHub credentials with keys:
            login: the GitHub login for the credential
            token: the API token for the credential
            x_ratelimit_*: the rate-limit info for the given credential

    Returns:
        a dict with the following keys:
            credential_used: the login for the credential used
            x_ratelimit_*: GitHub rate-limiting information
    """
    print("Requesting url %s" % url)
    if not session:
        session = requests

    headers = {
        'Accept': 'application/vnd.github.v3+json',
    }

    if etag:
        headers['If-None-Match'] = etag
    else:
        if last_modified:
            headers['If-Modified-Since'] = last_modified

    if not credentials:
        credentials = {None: {}}

    reply = None
    ret = {}
    for login, creds in credentials.items():
        # Handle rate-limiting
        remaining = creds.get('x_ratelimit_remaining')
        reset = creds.get('x_ratelimit_reset')
        if remaining == 0 and reset and reset > time.time():
            continue

        kwargs = {}
        if login and creds['token']:
            kwargs['auth'] = (login, creds['token'])

        reply = session.get(url, headers=headers, **kwargs)

        ratelimit = {
            key.lower().replace('-', '_'): int(value)
            for key, value in reply.headers.items()
            if key.lower().startswith('x-ratelimit')
        }

        ret.update(ratelimit)
        creds.update(ratelimit)

        if not(reply.status_code == 403 and
               ratelimit.get('x_ratelimit_remaining') == 0):
            # Request successful, let's get out of here
            break
    else:
        # we broke out of the loop
        raise ValueError('All out of credentials', credentials)

    etag = reply.headers.get('ETag')
    if etag and etag.startswith(('w/', 'W/')):
        # Strip down reference to "weak" etags
        etag = etag[2:]

    ret.update({
        'url': url,
        'code': reply.status_code,
        'data': reply.json() if reply.status_code != 304 else None,
        'etag': etag,
        'last_modified': reply.headers.get('Last-Modified'),
        'links': reply.links,
        'login': login,
    })

    return ret


def repositories(since=0, url=None, session=None, credentials=None):
    """Request the list of public repositories with id greater than `since`"""
    if not url:
        url = urljoin(GITHUB_API_BASE, 'repositories?since=%s' % since)

    req = github_api_request(url, session=session, credentials=credentials)

    return req


def repository(id, session=None, credentials=None, last_modified=None):
    """Request the information on the repository with the given id"""
    url = urljoin(GITHUB_API_BASE, 'repositories/%d' % id)
    req = github_api_request(url, session=session, credentials=credentials,
                             last_modified=last_modified)

    return req


def forks(id, page, session=None, credentials=None):
    """Request the information on the repository with the given id"""
    url = urljoin(GITHUB_API_BASE,
                  'repositories/%d/forks?sort=oldest&page=%d' % (id, page))
    req = github_api_request(url, session=session, credentials=credentials)

    return req


def user(id, session=None, credentials=None, last_modified=None):
    """Request the information on the user with the given id"""
    url = urljoin(GITHUB_API_BASE, 'user/%d' % id)
    req = github_api_request(url, session=session, credentials=credentials,
                             last_modified=last_modified)

    return req
