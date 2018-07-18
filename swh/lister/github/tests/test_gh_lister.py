# Copyright (C) 2017-2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import re
import unittest
from datetime import datetime, timedelta

from swh.lister.core.tests.test_lister import HttpListerTester
from swh.lister.github.lister import GitHubLister


class GitHubListerTester(HttpListerTester, unittest.TestCase):
    Lister = GitHubLister
    test_re = re.compile(r'/repositories\?since=([^?&]+)')
    lister_subdir = 'github'
    good_api_response_file = 'api_response.json'
    bad_api_response_file = 'api_empty_response.json'
    first_index = 26
    last_index = 368
    entries_per_page = 100

    def response_headers(self, request):
        headers = {'X-RateLimit-Remaining': '1'}
        if self.request_index(request) == str(self.first_index):
            headers.update({
                'Link': '<https://api.github.com/repositories?since=367>;'
                        ' rel="next",'
                        '<https://api.github.com/repositories{?since}>;'
                        ' rel="first"'
            })
        else:
            headers.update({
                'Link': '<https://api.github.com/repositories{?since}>;'
                        ' rel="first"'
            })

        return headers

    def mock_rate_quota(self, n, request, context):
        self.rate_limit += 1
        context.status_code = 403
        context.headers['X-RateLimit-Remaining'] = '0'
        one_second = int((datetime.now() + timedelta(seconds=1.5)).timestamp())
        context.headers['X-RateLimit-Reset'] = str(one_second)
        return '{"error":"dummy"}'
