# Copyright (C) 2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json
import logging
import re
import unittest

import requests_mock

from swh.lister.core.tests.test_lister import HttpListerTester
from swh.lister.phabricator.lister import PhabricatorLister, get_repo_url

logger = logging.getLogger(__name__)


class PhabricatorListerTester(HttpListerTester, unittest.TestCase):
    Lister = PhabricatorLister
    # first request will have the after parameter empty
    test_re = re.compile(r"\&after=([^?&]*)")
    lister_subdir = "phabricator"
    good_api_response_file = "data/api_first_response.json"
    good_api_response_undefined_protocol = "data/api_response_undefined_protocol.json"
    bad_api_response_file = "data/api_empty_response.json"
    # first_index must be retrieved through a bootstrap process for Phabricator
    first_index = None
    last_index = 12
    entries_per_page = 10

    convert_type = int

    def request_index(self, request):
        """(Override) This is needed to emulate the listing bootstrap
        when no min_bound is provided to run
        """
        m = self.test_re.search(request.path_url)
        idx = m.group(1)
        if idx not in ("", "None"):
            return int(idx)

    def get_fl(self, override_config=None):
        """(Override) Retrieve an instance of fake lister (fl).

        """
        if override_config or self.fl is None:
            credentials = {"phabricator": {"fake": [{"password": "toto"}]}}
            override_config = dict(credentials=credentials, **(override_config or {}))
            self.fl = self.Lister(
                url="https://fakeurl", instance="fake", override_config=override_config
            )
            self.fl.INITIAL_BACKOFF = 1

        self.fl.reset_backoff()
        return self.fl

    def test_get_repo_url(self):
        f = open(
            "swh/lister/%s/tests/%s" % (self.lister_subdir, self.good_api_response_file)
        )
        api_response = json.load(f)
        repos = api_response["result"]["data"]
        for repo in repos:
            self.assertEqual(
                "https://forge.softwareheritage.org/source/%s.git"
                % (repo["fields"]["shortName"]),
                get_repo_url(repo["attachments"]["uris"]["uris"]),
            )

        f = open(
            "swh/lister/%s/tests/%s"
            % (self.lister_subdir, self.good_api_response_undefined_protocol)
        )
        repo = json.load(f)
        self.assertEqual(
            "https://svn.blender.org/svnroot/bf-blender/",
            get_repo_url(repo["attachments"]["uris"]["uris"]),
        )

    @requests_mock.Mocker()
    def test_scheduled_tasks(self, http_mocker):
        self.scheduled_tasks_test("data/api_next_response.json", 23, http_mocker)

    @requests_mock.Mocker()
    def test_scheduled_tasks_multiple_instances(self, http_mocker):

        fl = self.create_fl_with_db(http_mocker)

        # list first Phabricator instance
        fl.run()

        fl.instance = "other_fake"
        fl.config["credentials"] = {
            "phabricator": {"other_fake": [{"password": "foo"}]}
        }

        # list second Phabricator instance hosting repositories having
        # same ids as those listed from the first instance
        self.good_api_response_file = "data/api_first_response_other_instance.json"
        self.last_index = 13
        fl.run()

        # check expected number of loading tasks
        self.assertEqual(len(self.scheduler_tasks), 2 * self.entries_per_page)

        # check tasks are not disabled
        for task in self.scheduler_tasks:
            self.assertTrue(task["status"] != "disabled")


def test_phabricator_lister(lister_phabricator, requests_mock_datadir):
    lister = lister_phabricator
    assert lister.url == lister.DEFAULT_URL
    assert lister.instance == "forge.softwareheritage.org"
    lister.run()

    r = lister.scheduler.search_tasks(task_type="load-git")
    assert len(r) == 10

    for row in r:
        assert row["type"] == "load-git"
        # arguments check
        args = row["arguments"]["args"]
        assert len(args) == 0

        # kwargs
        kwargs = row["arguments"]["kwargs"]
        url = kwargs["url"]
        assert lister.instance in url

        assert row["policy"] == "recurring"
        assert row["priority"] is None
