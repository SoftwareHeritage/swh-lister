# Copyright (C) 2017-2021 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json
import logging
from pathlib import Path
from typing import Dict, List

import pytest

from swh.lister import USER_AGENT
from swh.lister.gitlab.lister import GitLabLister, _parse_page_id
from swh.lister.pattern import ListerStats

logger = logging.getLogger(__name__)


def api_url(instance: str) -> str:
    return f"https://{instance}/api/v4/"


def url_page(api_url: str, page_id: int) -> str:
    return f"{api_url}projects?page={page_id}&order_by=id&sort=asc&per_page=20"


def _match_request(request):
    return request.headers.get("User-Agent") == USER_AGENT


def test_lister_gitlab(datadir, swh_scheduler, requests_mock):
    """Gitlab lister supports full listing

    """
    instance = "gitlab.com"
    url = api_url(instance)

    response = gitlab_page_response(datadir, instance, 1)

    requests_mock.get(
        url_page(url, 1), [{"json": response}], additional_matcher=_match_request,
    )

    lister_gitlab = GitLabLister(
        swh_scheduler, url=api_url(instance), instance=instance
    )

    listed_result = lister_gitlab.run()
    expected_nb_origins = len(response)
    assert listed_result == ListerStats(pages=1, origins=expected_nb_origins)

    scheduler_origins = lister_gitlab.scheduler.get_listed_origins(
        lister_gitlab.lister_obj.id
    ).origins
    assert len(scheduler_origins) == expected_nb_origins

    for listed_origin in scheduler_origins:
        assert listed_origin.visit_type == "git"
        assert listed_origin.url.startswith(f"https://{instance}")


def gitlab_page_response(datadir, instance: str, page_id: int) -> List[Dict]:
    """Return list of repositories (out of test dataset)"""
    datapath = Path(datadir, f"https_{instance}", f"api_response_page{page_id}.json")
    return json.loads(datapath.read_text()) if datapath.exists else []


def test_lister_gitlab_with_pages(swh_scheduler, requests_mock, datadir):
    """Gitlab lister supports pagination

    """
    instance = "gite.lirmm.fr"
    url = api_url(instance)

    response1 = gitlab_page_response(datadir, instance, 1)
    response2 = gitlab_page_response(datadir, instance, 2)

    requests_mock.get(
        url_page(url, 1),
        [{"json": response1, "headers": {"Link": f"<{url_page(url, 2)}>; rel=next"}}],
        additional_matcher=_match_request,
    )

    requests_mock.get(
        url_page(url, 2), [{"json": response2}], additional_matcher=_match_request,
    )

    lister = GitLabLister(swh_scheduler, url=url)
    listed_result = lister.run()

    expected_nb_origins = len(response1) + len(response2)
    assert listed_result == ListerStats(pages=2, origins=expected_nb_origins)

    scheduler_origins = lister.scheduler.get_listed_origins(
        lister.lister_obj.id
    ).origins
    assert len(scheduler_origins) == expected_nb_origins

    for listed_origin in scheduler_origins:
        assert listed_origin.visit_type == "git"
        assert listed_origin.url.startswith(f"https://{instance}")


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
