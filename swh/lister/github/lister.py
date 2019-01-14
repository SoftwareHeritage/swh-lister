# Copyright (C) 2017-2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import re
import time

from swh.lister.core.indexing_lister import SWHIndexingHttpLister
from swh.lister.github.models import GitHubModel


class GitHubLister(SWHIndexingHttpLister):
    PATH_TEMPLATE = '/repositories?since=%d'
    MODEL = GitHubModel
    API_URL_INDEX_RE = re.compile(r'^.*/repositories\?since=(\d+)')
    LISTER_NAME = 'github'

    def get_model_from_repo(self, repo):
        return {
            'uid': repo['id'],
            'indexable': repo['id'],
            'name': repo['name'],
            'full_name': repo['full_name'],
            'html_url': repo['html_url'],
            'origin_url': repo['html_url'],
            'origin_type': 'git',
            'description': repo['description'],
            'fork': repo['fork'],
        }

    def transport_quota_check(self, response):
        reqs_remaining = int(response.headers['X-RateLimit-Remaining'])
        if response.status_code == 403 and reqs_remaining == 0:
            reset_at = int(response.headers['X-RateLimit-Reset'])
            delay = min(reset_at - time.time(), 3600)
            return True, delay
        else:
            return False, 0

    def get_next_target_from_response(self, response):
        if 'next' in response.links:
            next_url = response.links['next']['url']
            return int(self.API_URL_INDEX_RE.match(next_url).group(1))
        else:
            return None

    def transport_response_simplified(self, response):
        repos = response.json()
        return [self.get_model_from_repo(repo) for repo in repos]

    def request_headers(self):
        return {'Accept': 'application/vnd.github.v3+json'}
