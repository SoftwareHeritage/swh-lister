# Copyright (C) 2020-2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from datetime import datetime
import json
from pathlib import Path
from typing import List

import pytest

from ..lister import LaunchpadLister


class _Repo:
    def __init__(self, d: dict):
        for key in d.keys():
            if key == "date_last_modified":
                setattr(self, key, datetime.fromisoformat(d[key]))
            else:
                setattr(self, key, d[key])


class _Collection:
    entries: List[_Repo] = []

    def __init__(self, file):
        self.entries = [_Repo(r) for r in file]

    def __getitem__(self, key):
        return self.entries[key]

    def __len__(self):
        return len(self.entries)


def _launchpad_response(datadir, datafile):
    return _Collection(json.loads(Path(datadir, datafile).read_text()))


@pytest.fixture
def launchpad_response1(datadir):
    return _launchpad_response(datadir, "launchpad_response1.json")


@pytest.fixture
def launchpad_response2(datadir):
    return _launchpad_response(datadir, "launchpad_response2.json")


def _mock_getRepositories(mocker, launchpad_response):
    mock_launchpad = mocker.patch("swh.lister.launchpad.lister.Launchpad")
    mock_getRepositories = mock_launchpad.git_repositories.getRepositories
    mock_getRepositories.return_value = launchpad_response
    mock_launchpad.login_anonymously.return_value = mock_launchpad

    return mock_getRepositories


def _check_listed_origins(scheduler_origins, launchpad_response):
    for origin in launchpad_response:

        filtered_origins = [
            o for o in scheduler_origins if o.url == origin.git_https_url
        ]

        assert len(filtered_origins) == 1

        assert filtered_origins[0].last_update == origin.date_last_modified


def test_lister_from_configfile(swh_scheduler_config, mocker):
    load_from_envvar = mocker.patch("swh.lister.pattern.load_from_envvar")
    load_from_envvar.return_value = {
        "scheduler": {"cls": "local", **swh_scheduler_config},
        "credentials": {},
    }
    lister = LaunchpadLister.from_configfile()
    assert lister.scheduler is not None
    assert lister.credentials is not None


def test_launchpad_full_lister(swh_scheduler, mocker, launchpad_response1):
    mock_getRepositories = _mock_getRepositories(mocker, launchpad_response1)
    lister = LaunchpadLister(scheduler=swh_scheduler)
    stats = lister.run()

    assert not lister.incremental
    assert lister.updated
    assert stats.pages == 1
    assert stats.origins == len(launchpad_response1)

    mock_getRepositories.assert_called_once_with(
        order_by="most neglected first", modified_since_date=None
    )

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    assert len(scheduler_origins) == len(launchpad_response1)

    _check_listed_origins(scheduler_origins, launchpad_response1)


def test_launchpad_incremental_lister(
    swh_scheduler, mocker, launchpad_response1, launchpad_response2
):
    mock_getRepositories = _mock_getRepositories(mocker, launchpad_response1)
    lister = LaunchpadLister(scheduler=swh_scheduler, incremental=True)
    stats = lister.run()

    assert lister.incremental
    assert lister.updated
    assert stats.pages == 1
    assert stats.origins == len(launchpad_response1)

    mock_getRepositories.assert_called_once_with(
        order_by="most neglected first", modified_since_date=None
    )

    lister_state = lister.get_state_from_scheduler()
    assert lister_state.date_last_modified == launchpad_response1[-1].date_last_modified

    mock_getRepositories = _mock_getRepositories(mocker, launchpad_response2)
    lister = LaunchpadLister(scheduler=swh_scheduler, incremental=True)
    stats = lister.run()

    assert lister.incremental
    assert lister.updated
    assert stats.pages == 1
    assert stats.origins == len(launchpad_response2)

    mock_getRepositories.assert_called_once_with(
        order_by="most neglected first",
        modified_since_date=lister_state.date_last_modified,
    )

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    assert len(scheduler_origins) == len(launchpad_response1) + len(launchpad_response2)

    _check_listed_origins(scheduler_origins, launchpad_response1)
    _check_listed_origins(scheduler_origins, launchpad_response2)


def test_launchpad_lister_invalid_url_filtering(
    swh_scheduler, mocker,
):
    invalid_origin = [_Repo({"git_https_url": "tag:launchpad.net:2008:redacted",})]
    _mock_getRepositories(mocker, invalid_origin)
    lister = LaunchpadLister(scheduler=swh_scheduler)
    stats = lister.run()

    assert not lister.updated
    assert stats.pages == 1
    assert stats.origins == 0


def test_launchpad_lister_duplicated_origin(
    swh_scheduler, mocker,
):
    origin = _Repo(
        {
            "git_https_url": "https://git.launchpad.net/test",
            "date_last_modified": "2021-01-14 21:05:31.231406+00:00",
        }
    )
    origins = [origin, origin]
    _mock_getRepositories(mocker, origins)
    lister = LaunchpadLister(scheduler=swh_scheduler)
    stats = lister.run()

    assert lister.updated
    assert stats.pages == 1
    assert stats.origins == 1
