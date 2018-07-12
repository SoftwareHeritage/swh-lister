# Copyright (C) 2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import random
import time

from .. import utils
from ..core.paging_lister import PageByPageHttpLister
from .models import GitLabModel


class GitLabLister(PageByPageHttpLister):
    # Template path expecting an integer that represents the page id
    PATH_TEMPLATE = '/projects?page=%d&order_by=id'
    MODEL = GitLabModel
    LISTER_NAME = 'gitlab'

    def __init__(self, api_baseurl=None, instance=None,
                 override_config=None, sort='asc'):
        super().__init__(api_baseurl=api_baseurl,
                         override_config=override_config)
        self.instance = instance
        self.PATH_TEMPLATE = '%s&sort=%s' % (self.PATH_TEMPLATE, sort)

    @property
    def ADDITIONAL_CONFIG(self):
        """Override additional config as the 'credentials' structure change
           between the ancestor classes and this class.

           cf. request_params method below

        """
        default_config = super().ADDITIONAL_CONFIG
        # 'credentials' is a dict of (instance, {username, password}) dict
        default_config['credentials'] = ('dict', {})
        return default_config

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
            creds_lister = creds[self.instance]
            auth = random.choice(creds_lister) if creds else None
            if auth:
                params['auth'] = (auth['username'], auth['password'])
        return params

    def get_model_from_repo(self, repo):
        return {
            'instance': self.instance,
            'uid': repo['id'],
            'name': repo['name'],
            'full_name': repo['path_with_namespace'],
            'html_url': repo['web_url'],
            'origin_url': repo['http_url_to_repo'],
            'origin_type': 'git',
            'description': repo['description'],
        }

    def transport_quota_check(self, response):
        """Deal with rate limit if any.

        """
        # not all gitlab instance have rate limit
        if 'RateLimit-Remaining' in response.headers:
            reqs_remaining = int(response.headers['RateLimit-Remaining'])
            if response.status_code == 403 and reqs_remaining == 0:
                reset_at = int(response.headers['RateLimit-Reset'])
                delay = min(reset_at - time.time(), 3600)
                return True, delay
        return False, 0

    def get_next_target_from_response(self, response):
        """Determine the next page identifier.

        """
        _next = utils.get(response.headers, ['X-Next-Page', 'x-next-page'])
        if _next:
            return int(_next)

    def get_pages_information(self):
        """Determine pages information.

        """
        response = self.transport_head(identifier=1)
        h = response.headers
        total = utils.get(h, ['X-Total', 'x-total'])
        total_pages = utils.get(h, ['X-Total-Pages', 'x-total-pages'])
        per_page = utils.get(h, ['X-Per-Page', 'x-per-page'])
        if total is not None:
            total = int(total)
        if total_pages is not None:
            total_pages = int(total_pages)
        if per_page is not None:
            per_page = int(per_page)
        return total, total_pages, per_page

    def transport_response_simplified(self, response):
        repos = response.json()
        return [self.get_model_from_repo(repo) for repo in repos]
