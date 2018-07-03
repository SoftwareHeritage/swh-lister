# Copyright (C) 2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import random
import re
import time

from ..core.paging_lister import SWHPagingHttpLister
from .models import GitLabModel


class GitLabLister(SWHPagingHttpLister):
    # Template path expecting an integer that represents the page id
    PATH_TEMPLATE = '/projects?page=%d&order_by=id&sort=asc&simple=true'
    API_URL_INDEX_RE = re.compile(r'^.*/projects.*\&page=(\d+).*')
    MODEL = GitLabModel

    @property
    def CONFIG_BASE_FILENAME(self):
        """One gitlab lister for all instances.  We discriminate between the
        origin on a per instance basis in the table.

        """
        return 'lister-gitlab'

    @property
    def ADDITIONAL_CONFIG(self):
        """Override additional config as the 'credentials' structure change
           between the ancestor classes and the subclass.

           cf. request_params method below

        """
        return {
            'lister_db_url':
                ('str', 'postgresql:///lister-gitlab'),
            'credentials':  # credentials is a dict
                ('dict', {}),
            'cache_responses':
                ('bool', False),
            'cache_dir':
                ('str', '~/.cache/swh/lister/%s' % self.lister_name),
        }

    def request_params(self, identifier):
        """Get the full parameters passed to requests given the
        transport_request identifier.

        For the gitlab lister, the 'credentials' entries is configured
        per instance. For example:

        - credentials:
          - gitlab.com:
            - username: user0
              password: <pass>
            - username: user1
              password: <pass>
            - ...
          - other-gitlab-instance:
            ...

        """
        params = {
            'headers': self.request_headers() or {}
        }
        # Retrieve the credentials per instance
        creds = self.config['credentials']
        if creds:
            creds_lister = creds[self.lister_name]
            auth = random.choice(creds_lister) if creds else None
            if auth:
                params['auth'] = (auth['username'], auth['password'])
        return params

    def get_model_from_repo(self, repo):
        return {
            'instance': self.lister_name,
            'uid': repo['id'],
            'indexable': repo['id'],
            'name': repo['name'],
            'full_name': repo['path_with_namespace'],
            'html_url': repo['web_url'],
            'origin_url': repo['http_url_to_repo'],
            'origin_type': 'git',
            'description': repo['description'],
        }

    def transport_quota_check(self, response):
        """Deal with rate limit

        """
        reqs_remaining = int(response.headers['RateLimit-Remaining'])
        # TODO: need to dig further about the actual returned code
        # (not seen yet in documentation)
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
