# Copyright (C) 2017-2020 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from datetime import datetime, timedelta
import logging
import re
import unittest

import pytest

from swh.lister.core.tests.test_lister import HttpListerTesterBase
from swh.lister.gitlab.lister import GitLabLister

logger = logging.getLogger(__name__)


class GitLabListerTester(HttpListerTesterBase, unittest.TestCase):
    Lister = GitLabLister
    test_re = re.compile(r"^.*/projects.*page=(\d+).*")
    lister_subdir = "gitlab"
    good_api_response_file = "data/gitlab.com/api_response.json"
    bad_api_response_file = "data/gitlab.com/api_empty_response.json"
    first_index = 1
    entries_per_page = 10
    convert_type = int

    def response_headers(self, request):
        headers = {"RateLimit-Remaining": "1"}
        if self.request_index(request) == self.first_index:
            headers.update(
                {"x-next-page": "3",}
            )

        return headers

    def mock_rate_quota(self, n, request, context):
        self.rate_limit += 1
        context.status_code = 403
        context.headers["RateLimit-Remaining"] = "0"
        one_second = int((datetime.now() + timedelta(seconds=1.5)).timestamp())
        context.headers["RateLimit-Reset"] = str(one_second)
        return '{"error":"dummy"}'


@pytest.fixture
def lister_under_test():
    return "gitlab"


def test_lister_gitlab(lister_gitlab, requests_mock_datadir):
    lister_gitlab.run()

    r = lister_gitlab.scheduler.search_tasks(task_type="load-git")
    assert len(r) == 10

    for row in r:
        assert row["type"] == "load-git"
        # arguments check
        args = row["arguments"]["args"]
        assert len(args) == 0

        # kwargs
        kwargs = row["arguments"]["kwargs"]
        url = kwargs["url"]
        assert url.startswith("https://gitlab.com")

        assert row["policy"] == "recurring"
        assert row["priority"] is None
