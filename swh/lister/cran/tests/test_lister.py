# Copyright (C) 2019-2020 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json
from os import path
from unittest.mock import patch

import pytest

from swh.lister.cran.lister import CRAN_MIRROR, compute_origin_urls


def test_cran_compute_origin_urls():
    pack = "something"
    vers = "0.0.1"
    origin_url, artifact_url = compute_origin_urls({"Package": pack, "Version": vers,})

    assert origin_url == f"{CRAN_MIRROR}/package={pack}"
    assert artifact_url == f"{CRAN_MIRROR}/src/contrib/{pack}_{vers}.tar.gz"


def test_cran_compute_origin_urls_failure():
    for incomplete_repo in [{"Version": "0.0.1"}, {"Package": "package"}, {}]:
        with pytest.raises(KeyError):
            compute_origin_urls(incomplete_repo)


@patch("swh.lister.cran.lister.read_cran_data")
def test_cran_lister_cran(mock_cran, datadir, lister_cran):
    with open(path.join(datadir, "list-r-packages.json")) as f:
        data = json.loads(f.read())

    mock_cran.return_value = data
    assert len(data) == 6

    lister_cran.run()

    r = lister_cran.scheduler.search_tasks(task_type="load-cran")
    assert len(r) == 6

    for row in r:
        assert row["type"] == "load-cran"
        # arguments check
        args = row["arguments"]["args"]
        assert len(args) == 0

        # kwargs
        kwargs = row["arguments"]["kwargs"]
        assert len(kwargs) == 2
        assert set(kwargs.keys()) == {"url", "artifacts"}

        artifacts = kwargs["artifacts"]
        assert len(artifacts) == 1

        assert set(artifacts[0].keys()) == {"url", "version"}

        assert row["policy"] == "oneshot"
        assert row["retries_left"] == 3

        origin_url = kwargs["url"]
        record = (
            lister_cran.db_session.query(lister_cran.MODEL)
            .filter(origin_url == origin_url)
            .first()
        )
        assert record
        assert record.uid == f"{record.name}-{record.version}"
