# Copyright (C) 2019-2020 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging

import pytest


logger = logging.getLogger(__name__)


@pytest.fixture
def lister_under_test():
    return "gnu"


@pytest.fixture
def test_gnu_lister(swh_lister, requests_mock_datadir):
    swh_lister.run()

    r = swh_lister.scheduler.search_tasks(task_type="load-archive-files")
    assert len(r) == 383

    for row in r:
        assert row["type"] == "load-archive-files"
        # arguments check
        args = row["arguments"]["args"]
        assert len(args) == 0

        # kwargs
        kwargs = row["arguments"]["kwargs"]
        assert set(kwargs.keys()) == {"url", "artifacts"}

        url = kwargs["url"]
        assert url.startswith("https://ftp.gnu.org")

        url_suffix = url.split("https://ftp.gnu.org")[1]
        assert "gnu" in url_suffix or "old-gnu" in url_suffix

        artifacts = kwargs["artifacts"]
        # check the artifact's structure
        artifact = artifacts[0]
        assert set(artifact.keys()) == {"url", "length", "time", "filename", "version"}

        for artifact in artifacts:
            logger.debug(artifact)
            # 'time' is an isoformat string now
            for key in ["url", "time", "filename", "version"]:
                assert isinstance(artifact[key], str)
            assert isinstance(artifact["length"], int)

        assert row["policy"] == "oneshot"
        assert row["priority"] is None
        assert row["retries_left"] == 3
