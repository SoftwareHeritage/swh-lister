# Copyright (C) 2017-2020 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging
import re
import unittest

from swh.lister.core.tests.test_lister import HttpListerTesterBase
from swh.lister.gitea.lister import GiteaLister

logger = logging.getLogger(__name__)


class GiteaListerTester(HttpListerTesterBase, unittest.TestCase):
    Lister = GiteaLister
    test_re = re.compile(r"^.*/projects.*page=(\d+).*")
    lister_subdir = "gitea"
    good_api_response_file = "data/https_try.gitea.io/api_response.json"
    bad_api_response_file = "data/https_try.gitea.io/api_empty_response.json"
    first_index = 1
    last_index = 2
    entries_per_page = 3
    convert_type = int

    def response_headers(self, request):
        headers = {}
        if self.request_index(request) == self.first_index:
            headers.update(
                {
                    "Link": "<https://try.gitea.io/api/v1\
                        /repos/search?&page=%s&sort=id>;"
                    ' rel="next"' % self.last_index
                }
            )

        return headers


def test_lister_gitea(lister_gitea, requests_mock_datadir):
    lister_gitea.run()
    r = lister_gitea.scheduler.search_tasks(task_type="load-git")
    assert len(r) == 3

    for row in r:
        assert row["type"] == "load-git"
        # arguments check
        args = row["arguments"]["args"]
        assert len(args) == 0

        # kwargs
        kwargs = row["arguments"]["kwargs"]
        url = kwargs["url"]
        assert url.startswith("https://try.gitea.io")

        assert row["policy"] == "recurring"
        assert row["priority"] is None
