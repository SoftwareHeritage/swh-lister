# Copyright (C) 2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import random
import time
from urllib3.util import parse_url

from ..core.page_by_page_lister import PageByPageHttpLister
from .models import GitLabModel


class GitLabLister(PageByPageHttpLister):
    # Template path expecting an integer that represents the page id
    PATH_TEMPLATE = '/projects?page=%d&order_by=id'
    MODEL = GitLabModel
    LISTER_NAME = 'gitlab'

    def __init__(self, api_baseurl, instance=None,
                 override_config=None, sort='asc', per_page=20):
        super().__init__(api_baseurl=api_baseurl,
                         override_config=override_config)
        if instance is None:
            instance = parse_url(api_baseurl).host
        self.instance = instance
        self.PATH_TEMPLATE = '%s&sort=%s' % (self.PATH_TEMPLATE, sort)
        if per_page != 20:
            self.PATH_TEMPLATE = '%s&per_page=%s' % (
                self.PATH_TEMPLATE, per_page)

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
        per instance. For example::

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
        creds_lister = self.config['credentials'].get(self.instance)
        if creds_lister:
            auth = random.choice(creds_lister)
            if auth:
                params['auth'] = (auth['username'], auth['password'])
        return params

    def uid(self, repo):
        return '%s/%s' % (self.instance, repo['path_with_namespace'])

    def get_model_from_repo(self, repo):
        return {
            'instance': self.instance,
            'uid': self.uid(repo),
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

    def _get_int(self, headers, key):
        _val = headers.get(key)
        if _val:
            return int(_val)

    def get_next_target_from_response(self, response):
        """Determine the next page identifier.

        """
        return self._get_int(response.headers, 'x-next-page')

    def get_pages_information(self):
        """Determine pages information.

        """
        response = self.transport_head(identifier=1)
        if not response.ok:
            raise ValueError(
                'Problem during information fetch: %s' % response.status_code)
        h = response.headers
        return (self._get_int(h, 'x-total'),
                self._get_int(h, 'x-total-pages'),
                self._get_int(h, 'x-per-page'))

    def transport_response_simplified(self, response):
        repos = response.json()
        return [self.get_model_from_repo(repo) for repo in repos]
