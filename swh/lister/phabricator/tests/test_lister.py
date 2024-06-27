# Copyright (C) 2019-2024  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json
from pathlib import Path

import pytest
from requests.exceptions import HTTPError

from swh.lister import USER_AGENT_TEMPLATE
from swh.lister.phabricator.lister import PhabricatorLister, get_repo_url


@pytest.fixture
def phabricator_repositories_page1(datadir):
    return json.loads(
        Path(datadir, "phabricator_api_repositories_page1.json").read_text()
    )


@pytest.fixture
def phabricator_repositories_page2(datadir):
    return json.loads(
        Path(datadir, "phabricator_api_repositories_page2.json").read_text()
    )


def test_get_repo_url(phabricator_repositories_page1):
    repos = phabricator_repositories_page1["result"]["data"]
    for repo in repos:
        expected_name = "https://forge.softwareheritage.org/source/%s.git" % (
            repo["fields"]["shortName"]
        )
        assert get_repo_url(repo["attachments"]["uris"]["uris"]) == expected_name


def test_get_repo_url_undefined_protocol():
    undefined_protocol_uris = [
        {
            "fields": {
                "uri": {
                    "raw": "https://svn.blender.org/svnroot/bf-blender/",
                    "display": "https://svn.blender.org/svnroot/bf-blender/",
                    "effective": "https://svn.blender.org/svnroot/bf-blender/",
                    "normalized": "svn.blender.org/svnroot/bf-blender",
                },
                "builtin": {"protocol": None, "identifier": None},
            },
        }
    ]
    expected_name = "https://svn.blender.org/svnroot/bf-blender/"
    assert get_repo_url(undefined_protocol_uris) == expected_name


def test_lister_url_param(swh_scheduler):
    FORGE_BASE_URL = "https://forge.softwareheritage.org"
    API_REPOSITORY_PATH = "/api/diffusion.repository.search"

    for url in (
        FORGE_BASE_URL,
        f"{FORGE_BASE_URL}/",
        f"{FORGE_BASE_URL}/{API_REPOSITORY_PATH}",
        f"{FORGE_BASE_URL}/{API_REPOSITORY_PATH}/",
    ):
        lister = PhabricatorLister(
            scheduler=swh_scheduler, url=FORGE_BASE_URL, instance="swh", api_token="foo"
        )

        expected_url = f"{FORGE_BASE_URL}{API_REPOSITORY_PATH}"

        assert lister.url == expected_url


def test_lister(
    swh_scheduler,
    requests_mock,
    phabricator_repositories_page1,
    phabricator_repositories_page2,
):
    FORGE_BASE_URL = "https://forge.softwareheritage.org"
    API_TOKEN = "foo"

    lister = PhabricatorLister(
        scheduler=swh_scheduler, url=FORGE_BASE_URL, instance="swh", api_token=API_TOKEN
    )

    def match_request(request):
        return (
            request.headers.get("User-Agent")
            == USER_AGENT_TEMPLATE % PhabricatorLister.LISTER_NAME
            and f"api.token={API_TOKEN}" in request.body
        )

    requests_mock.post(
        f"{FORGE_BASE_URL}{lister.API_REPOSITORY_PATH}",
        [
            {"json": phabricator_repositories_page1},
            {"json": phabricator_repositories_page2},
        ],
        additional_matcher=match_request,
    )

    stats = lister.run()

    expected_nb_origins = len(phabricator_repositories_page1["result"]["data"]) * 2

    assert stats.pages == 2
    assert stats.origins == expected_nb_origins

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    assert len(scheduler_origins) == expected_nb_origins


def test_lister_request_error(
    swh_scheduler,
    requests_mock,
    phabricator_repositories_page1,
):
    FORGE_BASE_URL = "https://forge.softwareheritage.org"

    lister = PhabricatorLister(
        scheduler=swh_scheduler, url=FORGE_BASE_URL, instance="swh", api_token="foo"
    )

    requests_mock.post(
        f"{FORGE_BASE_URL}{lister.API_REPOSITORY_PATH}",
        [
            {"status_code": 200, "json": phabricator_repositories_page1},
            {"status_code": 500, "reason": "Internal Server Error"},
        ],
    )

    with pytest.raises(HTTPError):
        lister.run()
