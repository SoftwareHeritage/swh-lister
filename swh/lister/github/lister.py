# Copyright (C) 2017-2019 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import re
import time

from typing import Any

from swh.lister.core.indexing_lister import IndexingHttpLister
from swh.lister.github.models import GitHubModel


class GitHubLister(IndexingHttpLister):
    PATH_TEMPLATE = '/repositories?since=%d'
    MODEL = GitHubModel
    DEFAULT_URL = 'https://api.github.com'
    API_URL_INDEX_RE = re.compile(r'^.*/repositories\?since=(\d+)')
    LISTER_NAME = 'github'
    instance = 'github'  # There is only 1 instance of such lister
    default_min_bound = 0  # type: Any

    def get_model_from_repo(self, repo):
        return {
            'uid': repo['id'],
            'indexable': repo['id'],
            'name': repo['name'],
            'full_name': repo['full_name'],
            'html_url': repo['html_url'],
            'origin_url': repo['html_url'],
            'origin_type': 'git',
            'fork': repo['fork'],
        }

    def transport_quota_check(self, response):
        x_rate_limit_remaining = response.headers.get('X-RateLimit-Remaining')
        if not x_rate_limit_remaining:
            return False, 0
        reqs_remaining = int(x_rate_limit_remaining)
        if response.status_code == 403 and reqs_remaining == 0:
            reset_at = int(response.headers['X-RateLimit-Reset'])
            delay = min(reset_at - time.time(), 3600)
            return True, delay
        return False, 0

    def get_next_target_from_response(self, response):
        if 'next' in response.links:
            next_url = response.links['next']['url']
            return int(self.API_URL_INDEX_RE.match(next_url).group(1))

    def transport_response_simplified(self, response):
        repos = response.json()
        return [self.get_model_from_repo(repo) for repo in repos]

    def request_headers(self):
        """(Override) Set requests headers to send when querying the GitHub API

        """
        headers = super().request_headers()
        headers['Accept'] = 'application/vnd.github.v3+json'
        return headers

    def disable_deleted_repo_tasks(self, index, next_index, keep_these):
        """ (Overrides) Fix provided index value to avoid erroneously disabling
        some scheduler tasks
        """
        # Next listed repository ids are strictly greater than the 'since'
        # parameter, so increment the index to avoid disabling the latest
        # created task when processing a new repositories page returned by
        # the Github API
        return super().disable_deleted_repo_tasks(index + 1, next_index,
                                                  keep_these)
