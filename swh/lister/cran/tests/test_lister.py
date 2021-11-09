# Copyright (C) 2019-2021 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from datetime import datetime, timezone
import json
from os import path

import pytest

from swh.lister.cran.lister import (
    CRAN_MIRROR,
    CRANLister,
    compute_origin_urls,
    parse_packaged_date,
)


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


def test_parse_packaged_date():
    common_date_format = {
        "Package": "test",
        "Packaged": "2017-04-26 11:36:15 UTC; Jonathan",
    }
    assert parse_packaged_date(common_date_format) == datetime(
        year=2017, month=4, day=26, hour=11, minute=36, second=15, tzinfo=timezone.utc
    )
    common_date_format = {
        "Package": "test",
        "Packaged": "2017-04-26 11:36:15.123456 UTC; Jonathan",
    }
    assert parse_packaged_date(common_date_format) == datetime(
        year=2017,
        month=4,
        day=26,
        hour=11,
        minute=36,
        second=15,
        microsecond=123456,
        tzinfo=timezone.utc,
    )
    old_date_format = {
        "Package": "test",
        "Packaged": "Thu Mar 30 10:48:35 2006; hornik",
    }
    assert parse_packaged_date(old_date_format) == datetime(
        year=2006, month=3, day=30, hour=10, minute=48, second=35, tzinfo=timezone.utc
    )
    invalid_date_format = {
        "Package": "test",
        "Packaged": "foo",
    }
    assert parse_packaged_date(invalid_date_format) is None
    missing_date = {
        "Package": "test",
    }
    assert parse_packaged_date(missing_date) is None


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
            "artifacts": [
                {
                    "url": artifact_url,
                    "version": package_info["Version"],
                    "package": package_info["Package"],
                }
            ]
        }

        filtered_origins[0].last_update == parse_packaged_date(package_info)


def test_cran_lister_duplicated_origins(datadir, swh_scheduler, mocker):
    with open(path.join(datadir, "list-r-packages.json")) as f:
        cran_data = json.loads(f.read())

    lister = CRANLister(swh_scheduler)

    mock_cran = mocker.patch("swh.lister.cran.lister.read_cran_data")

    mock_cran.return_value = cran_data + cran_data

    stats = lister.run()

    assert stats.pages == 1
    assert stats.origins == len(cran_data)


@pytest.mark.parametrize(
    "credentials, expected_credentials",
    [
        (None, []),
        ({"key": "value"}, []),
        (
            {"CRAN": {"cran": [{"username": "user", "password": "pass"}]}},
            [{"username": "user", "password": "pass"}],
        ),
    ],
)
def test_lister_cran_instantiation_with_credentials(
    credentials, expected_credentials, swh_scheduler
):
    lister = CRANLister(swh_scheduler, credentials=credentials)

    # Credentials are allowed in constructor
    assert lister.credentials == expected_credentials


def test_lister_cran_from_configfile(swh_scheduler_config, mocker):
    load_from_envvar = mocker.patch("swh.lister.pattern.load_from_envvar")
    load_from_envvar.return_value = {
        "scheduler": {"cls": "local", **swh_scheduler_config},
        "credentials": {},
    }
    lister = CRANLister.from_configfile()
    assert lister.scheduler is not None
    assert lister.credentials is not None
