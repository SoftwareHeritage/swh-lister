# Copyright (C) 2017-2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import re
import unittest
from datetime import datetime, timedelta

from swh.lister.core.tests.test_lister import HttpListerTesterBase
from swh.lister.gitlab.lister import GitLabLister


class GitLabListerTester(HttpListerTesterBase, unittest.TestCase):
    Lister = GitLabLister
    test_re = re.compile(r'^.*/projects.*page=(\d+).*')
    lister_subdir = 'gitlab'
    good_api_response_file = 'api_response.json'
    bad_api_response_file = 'api_empty_response.json'
    first_index = 1
    entries_per_page = 10

    def response_headers(self, request):
        headers = {'RateLimit-Remaining': '1'}
        if self.request_index(request) == str(self.first_index):
            headers.update({
                'x-next-page': '3',
            })

        return headers

    def mock_rate_quota(self, n, request, context):
        self.rate_limit += 1
        context.status_code = 403
        context.headers['RateLimit-Remaining'] = '0'
        one_second = int((datetime.now() + timedelta(seconds=1.5)).timestamp())
        context.headers['RateLimit-Reset'] = str(one_second)
        return '{"error":"dummy"}'
