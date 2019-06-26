# Copyright (C) 2017-2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import re
import unittest

from datetime import timedelta

from urllib.parse import unquote

import iso8601
import requests_mock

from swh.lister.bitbucket.lister import BitBucketLister
from swh.lister.core.tests.test_lister import HttpListerTester


def convert_type(req_index):
    """Convert the req_index to its right type according to the model's
       "indexable" column.

    """
    return iso8601.parse_date(unquote(req_index))


class BitBucketListerTester(HttpListerTester, unittest.TestCase):
    Lister = BitBucketLister
    test_re = re.compile(r'/repositories\?after=([^?&]+)')
    lister_subdir = 'bitbucket'
    good_api_response_file = 'api_response.json'
    bad_api_response_file = 'api_empty_response.json'
    first_index = convert_type('2008-07-12T07:44:01.476818+00:00')
    last_index = convert_type('2008-07-19T06:16:43.044743+00:00')
    entries_per_page = 10
    convert_type = staticmethod(convert_type)

    @requests_mock.Mocker()
    def test_fetch_none_nodb(self, http_mocker):
        """Overridden because index is not an integer nor a string

        """
        http_mocker.get(self.test_re, text=self.mock_response)
        fl = self.get_fl()

        self.disable_scheduler(fl)
        self.disable_db(fl)

        # stores no results
        fl.run(min_bound=self.first_index - timedelta(days=3),
               max_bound=self.first_index)

    def test_is_within_bounds(self):
        fl = self.get_fl()
        self.assertTrue(fl.is_within_bounds(
            iso8601.parse_date('2008-07-15'),
            self.first_index, self.last_index))
        self.assertFalse(fl.is_within_bounds(
            iso8601.parse_date('2008-07-20'),
            self.first_index, self.last_index))
        self.assertFalse(fl.is_within_bounds(
            iso8601.parse_date('2008-07-11'),
            self.first_index, self.last_index))
