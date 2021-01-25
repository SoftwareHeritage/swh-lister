# Copyright (C) 2017-2021 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from datetime import datetime
import json
import os

import pytest

from swh.lister.bitbucket.lister import BitbucketLister


@pytest.fixture
def bb_api_repositories_page1(datadir):
    data_file_path = os.path.join(datadir, "bb_api_repositories_page1.json")
    with open(data_file_path, "r") as data_file:
        return json.load(data_file)


@pytest.fixture
def bb_api_repositories_page2(datadir):
    data_file_path = os.path.join(datadir, "bb_api_repositories_page2.json")
    with open(data_file_path, "r") as data_file:
        return json.load(data_file)


def _check_listed_origins(lister_origins, scheduler_origins):
    """Asserts that the two collections have the same origins from the point of view of
    the lister"""

    sorted_lister_origins = list(sorted(lister_origins))
    sorted_scheduler_origins = list(sorted(scheduler_origins))

    assert len(sorted_lister_origins) == len(sorted_scheduler_origins)

    for lo, so in zip(sorted_lister_origins, sorted_scheduler_origins):
        assert lo.url == so.url
        assert lo.last_update == so.last_update


def test_bitbucket_incremental_lister(
    swh_scheduler,
    requests_mock,
    mocker,
    bb_api_repositories_page1,
    bb_api_repositories_page2,
):
    """Simple Bitbucket listing with two pages containing 10 origins"""

    requests_mock.get(
        BitbucketLister.API_URL,
        [{"json": bb_api_repositories_page1}, {"json": bb_api_repositories_page2},],
    )

    lister = BitbucketLister(scheduler=swh_scheduler, page_size=10)

    # First listing
    stats = lister.run()

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    assert stats.pages == 2
    assert stats.origins == 20
    assert len(scheduler_origins) == 20

    assert lister.updated
    lister_state = lister.get_state_from_scheduler()
    last_repo_cdate = lister_state.last_repo_cdate.isoformat()
    assert hasattr(lister_state, "last_repo_cdate")
    assert last_repo_cdate == bb_api_repositories_page2["values"][-1]["created_on"]

    # Second listing, restarting from last state
    lister.session.get = mocker.spy(lister.session, "get")

    lister.run()

    url_params = lister.url_params
    url_params["after"] = last_repo_cdate

    lister.session.get.assert_called_once_with(lister.API_URL, params=url_params)

    all_origins = (
        bb_api_repositories_page1["values"] + bb_api_repositories_page2["values"]
    )

    _check_listed_origins(lister.get_origins_from_page(all_origins), scheduler_origins)


def test_bitbucket_lister_rate_limit_hit(
    swh_scheduler,
    requests_mock,
    mocker,
    bb_api_repositories_page1,
    bb_api_repositories_page2,
):
    """Simple Bitbucket listing with two pages containing 10 origins"""

    requests_mock.get(
        BitbucketLister.API_URL,
        [
            {"json": bb_api_repositories_page1, "status_code": 200},
            {"json": None, "status_code": 429},
            {"json": None, "status_code": 429},
            {"json": bb_api_repositories_page2, "status_code": 200},
        ],
    )

    lister = BitbucketLister(scheduler=swh_scheduler, page_size=10)

    mocker.patch.object(lister.page_request.retry, "sleep")

    stats = lister.run()

    assert stats.pages == 2
    assert stats.origins == 20
    assert len(swh_scheduler.get_listed_origins(lister.lister_obj.id).results) == 20


def test_bitbucket_full_lister(
    swh_scheduler,
    requests_mock,
    mocker,
    bb_api_repositories_page1,
    bb_api_repositories_page2,
):
    """Simple Bitbucket listing with two pages containing 10 origins"""

    requests_mock.get(
        BitbucketLister.API_URL,
        [
            {"json": bb_api_repositories_page1},
            {"json": bb_api_repositories_page2},
            {"json": bb_api_repositories_page1},
            {"json": bb_api_repositories_page2},
        ],
    )

    credentials = {"bitbucket": {"bitbucket": [{"username": "u", "password": "p"}]}}
    lister = BitbucketLister(
        scheduler=swh_scheduler, page_size=10, incremental=True, credentials=credentials
    )
    assert lister.session.auth is not None

    # First do a incremental run to have an initial lister state
    stats = lister.run()

    last_lister_state = lister.get_state_from_scheduler()

    assert stats.origins == 20

    # Then do the full run and verify lister state did not change
    # Modify last listed repo modification date to check it will be not saved
    # to lister state after its execution
    last_page2_repo = bb_api_repositories_page2["values"][-1]
    last_page2_repo["created_on"] = datetime.now().isoformat()
    last_page2_repo["updated_on"] = datetime.now().isoformat()

    lister = BitbucketLister(scheduler=swh_scheduler, page_size=10, incremental=False)
    assert lister.session.auth is None

    stats = lister.run()

    assert stats.pages == 2
    assert stats.origins == 20

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    # 20 because scheduler upserts based on (id, type, url)
    assert len(scheduler_origins) == 20

    # Modification on created_on SHOULD NOT impact lister state
    assert lister.get_state_from_scheduler() == last_lister_state

    # Modification on updated_on SHOULD impact lister state
    all_origins = (
        bb_api_repositories_page1["values"] + bb_api_repositories_page2["values"]
    )

    _check_listed_origins(lister.get_origins_from_page(all_origins), scheduler_origins)
