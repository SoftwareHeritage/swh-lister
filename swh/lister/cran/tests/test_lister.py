# Copyright (C) 2019-2021 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json
from os import path

import pytest

from swh.lister.cran.lister import CRAN_MIRROR, CRANLister, compute_origin_urls


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


def test_cran_lister_cran(datadir, swh_scheduler, mocker):
    with open(path.join(datadir, "list-r-packages.json")) as f:
        cran_data = json.loads(f.read())

    lister = CRANLister(swh_scheduler)

    mock_cran = mocker.patch("swh.lister.cran.lister.read_cran_data")

    mock_cran.return_value = cran_data

    stats = lister.run()

    assert stats.pages == 1
    assert stats.origins == len(cran_data)

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    assert len(scheduler_origins) == len(cran_data)

    for package_info in cran_data:
        origin_url, artifact_url = compute_origin_urls(package_info)

        filtered_origins = [o for o in scheduler_origins if o.url == origin_url]

        assert len(filtered_origins) == 1

        assert filtered_origins[0].extra_loader_arguments == {
            "artifacts": [{"url": artifact_url, "version": package_info["Version"]}]
        }
