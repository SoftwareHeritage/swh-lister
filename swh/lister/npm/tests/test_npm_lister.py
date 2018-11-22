# Copyright (C) 2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import re
import requests_mock
import unittest

from swh.lister.core.tests.test_lister import HttpListerTesterBase
from swh.lister.npm.lister import NpmLister


class NpmListerTester(HttpListerTesterBase, unittest.TestCase):
    Lister = NpmLister
    test_re = re.compile(r'^.*/_all_docs\?startkey=%22(.+)%22.*')
    lister_subdir = 'npm'
    good_api_response_file = 'api_response.json'
    bad_api_response_file = 'api_empty_response.json'
    first_index = 'jquery'
    entries_per_page = 100

    @requests_mock.Mocker()
    def test_is_within_bounds(self, http_mocker):
        # disable this test from HttpListerTesterBase as
        # it can not succeed for the npm lister due to the
        # overriding of the string_pattern_check method
        pass
