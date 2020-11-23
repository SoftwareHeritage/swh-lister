# Copyright (C) 2018-2019 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging
import re
from typing import Any, List
import unittest

import requests_mock

from swh.lister.core.tests.test_lister import HttpListerTesterBase
from swh.lister.npm.lister import NpmIncrementalLister, NpmLister

logger = logging.getLogger(__name__)


class NpmListerTester(HttpListerTesterBase, unittest.TestCase):
    Lister = NpmLister
    test_re = re.compile(r'^.*/_all_docs\?startkey="(.+)".*')
    lister_subdir = "npm"
    good_api_response_file = "data/replicate.npmjs.com/api_response.json"
    bad_api_response_file = "data/api_empty_response.json"
    first_index = "jquery"
    entries_per_page = 100

    @requests_mock.Mocker()
    def test_is_within_bounds(self, http_mocker):
        # disable this test from HttpListerTesterBase as
        # it can not succeed for the npm lister due to the
        # overriding of the string_pattern_check method
        pass


class NpmIncrementalListerTester(HttpListerTesterBase, unittest.TestCase):
    Lister = NpmIncrementalLister
    test_re = re.compile(r"^.*/_changes\?since=([0-9]+).*")
    lister_subdir = "npm"
    good_api_response_file = "data/api_inc_response.json"
    bad_api_response_file = "data/api_inc_empty_response.json"
    first_index = "6920642"
    entries_per_page = 100

    @requests_mock.Mocker()
    def test_is_within_bounds(self, http_mocker):
        # disable this test from HttpListerTesterBase as
        # it can not succeed for the npm lister due to the
        # overriding of the string_pattern_check method
        pass


def check_tasks(tasks: List[Any]):
    """Ensure scheduled tasks are in the expected format.


    """
    for row in tasks:
        logger.debug("row: %s", row)
        assert row["type"] == "load-npm"
        # arguments check
        args = row["arguments"]["args"]
        assert len(args) == 0

        # kwargs
        kwargs = row["arguments"]["kwargs"]
        assert len(kwargs) == 1
        package_url = kwargs["url"]
        package_name = package_url.split("/")[-1]
        assert package_url == f"https://www.npmjs.com/package/{package_name}"

        assert row["policy"] == "recurring"
        assert row["priority"] is None


def test_npm_lister_basic_listing(lister_npm, requests_mock_datadir):
    lister_npm.run()

    tasks = lister_npm.scheduler.search_tasks(task_type="load-npm")
    assert len(tasks) == 100

    check_tasks(tasks)


def test_npm_lister_listing_pagination(lister_npm, requests_mock_datadir):
    lister = lister_npm
    # Patch per page pagination
    lister.per_page = 10 + 1
    lister.PATH_TEMPLATE = lister.PATH_TEMPLATE.replace(
        "&limit=1001", "&limit=%s" % lister.per_page
    )
    lister.run()

    tasks = lister.scheduler.search_tasks(task_type="load-npm")
    assert len(tasks) == 2 * 10  # only 2 files with 10 results each

    check_tasks(tasks)
