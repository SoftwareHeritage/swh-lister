# Copyright (C) 2017-2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import unittest

from datetime import datetime, timedelta

from swh.lister.gitlab.lister import GitLabLister
from swh.lister.core.tests.test_lister import HttpListerTesterBase


class GitLabListerTester(HttpListerTesterBase, unittest.TestCase):
    Lister = GitLabLister
    test_re = GitLabLister.API_URL_INDEX_RE
    lister_subdir = 'gitlab'
    good_api_response_file = 'api_response.json'
    bad_api_response_file = 'api_empty_response.json'
    first_index = 1
    last_index = 2
    entries_per_page = 10

    def response_headers(self, request):
        headers = {'RateLimit-Remaining': '1'}
        if self.request_index(request) == str(self.first_index):
            headers.update({
                'Link': '<https://gitlab.com/v4/projects?page=2>;'
                        ' rel="next",'
                        '<https://gitlab.com/v4/projects{?page}>;'
                        ' rel="first"'
            })
        else:
            headers.update({
                'Link': '<https://gitlab.com/v4/projects{?page}>;'
                        ' rel="first"'
            })

        return headers

    def mock_rate_quota(self, n, request, context):
        self.rate_limit += 1
        context.status_code = 403
        context.headers['RateLimit-Remaining'] = '0'
        one_second = int((datetime.now() + timedelta(seconds=1.5)).timestamp())
        context.headers['RateLimit-Reset'] = str(one_second)
        return '{"error":"dummy"}'
