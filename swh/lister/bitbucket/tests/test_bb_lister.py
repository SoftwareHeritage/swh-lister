# Copyright (C) 2017-2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import re
import unittest

from swh.lister.bitbucket.lister import BitBucketLister
from swh.lister.core.tests.test_lister import HttpListerTester


class BitBucketListerTester(HttpListerTester, unittest.TestCase):
    Lister = BitBucketLister
    test_re = re.compile(r'/repositories\?after=([^?&]+)')
    lister_subdir = 'bitbucket'
    good_api_response_file = 'api_response.json'
    bad_api_response_file = 'api_empty_response.json'
    first_index = '2008-07-12T07:44:01.476818+00:00'
    last_index = '2008-07-19T06:16:43.044743+00:00'
    entries_per_page = 10
