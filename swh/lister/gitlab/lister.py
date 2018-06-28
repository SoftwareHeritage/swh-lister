# Copyright (C) 2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import re
import time

from ..core.indexing_lister import SWHIndexingHttpLister
from .models import GitlabModel


class GitlabLister(SWHIndexingHttpLister):
    # Path to give and mentioning the last id for the next page
    PATH_TEMPLATE = '/projects?page=%d'
    # base orm model
    MODEL = GitlabModel
    # gitlab api do not have an indexable identifier so using the page
    # id
    API_URL_INDEX_RE = re.compile(r'^.*/projects.*\&page=(\d+).*')

    def get_model_from_repo(self, repo):
        return {
            'uid': repo['id'],
            'indexable': repo['id'],
            'name': repo['name'],
            'full_name': repo['path_with_namespace'],
            'html_url': repo['web_url'],
            'origin_url': repo['web_url'],
            'origin_type': 'git',
            'description': repo['description'],
            # FIXME: How to determine the fork nature?
            'fork': False,
        }

    def transport_quota_check(self, response):
        """Deal with ratelimit

        """
        reqs_remaining = int(response.headers['RateLimit-Remaining'])
        if response.status_code == 403 and reqs_remaining == 0:
            reset_at = int(response.headers['RateLimit-Reset'])
            delay = min(reset_at - time.time(), 3600)
            return True, delay
        return False, 0

    def get_next_target_from_response(self, response):
        """Deal with pagination

        """
        if 'next' in response.links:
            next_url = response.links['next']['url']
            return int(self.API_URL_INDEX_RE.match(next_url).group(1))
        return None

    def transport_response_simplified(self, response):
        repos = response.json()
        return [self.get_model_from_repo(repo) for repo in repos]
