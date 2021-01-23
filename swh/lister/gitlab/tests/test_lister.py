# Copyright (C) 2017-2021 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging

import pytest

from swh.lister.gitlab.lister import GitLabLister, _parse_page_id
from swh.lister.pattern import ListerStats

logger = logging.getLogger(__name__)


@pytest.fixture
def lister_gitlab(swh_scheduler):
    url = "https://gitlab.com/api/v4/"
    return GitLabLister(swh_scheduler, url=url)


# class GitLabListerTester(HttpListerTesterBase, unittest.TestCase):
#     Lister = GitLabLister
#     test_re = re.compile(r"^.*/projects.*page=(\d+).*")
#     lister_subdir = "gitlab"
#     good_api_response_file = "data/gitlab.com/api_response.json"
#     bad_api_response_file = "data/gitlab.com/api_empty_response.json"
#     first_index = 1
#     entries_per_page = 10
#     convert_type = int

#     def response_headers(self, request):
#         headers = {"RateLimit-Remaining": "1"}
#         if self.request_index(request) == self.first_index:
#             headers.update(
#                 {"x-next-page": "3",}
#             )

#         return headers

#     def mock_rate_quota(self, n, request, context):
#         self.rate_limit += 1
#         context.status_code = 403
#         context.headers["RateLimit-Remaining"] = "0"
#         one_second = int((datetime.now() + timedelta(seconds=1.5)).timestamp())
#         context.headers["RateLimit-Reset"] = str(one_second)
#         return '{"error":"dummy"}'


def test_lister_gitlab(lister_gitlab, requests_mock_datadir):
    listed_result = lister_gitlab.run()
    assert listed_result == ListerStats(pages=1, origins=10)

    scheduler_origins = lister_gitlab.scheduler.get_listed_origins(
        lister_gitlab.lister_obj.id
    ).origins
    assert len(scheduler_origins) == 10

    for listed_origin in scheduler_origins:
        assert listed_origin.visit_type == "git"
        assert listed_origin.url.startswith("https://gitlab.com")


@pytest.mark.parametrize(
    "url,expected_result",
    [
        (None, None),
        ("http://dummy/?query=1", None),
        ("http://dummy/?foo=bar&page=1&some=result", 1),
        ("http://dummy/?foo=bar&page=&some=result", None),
    ],
)
def test__parse_page_id(url, expected_result):
    assert _parse_page_id(url) == expected_result
