# Copyright (C) 2019-2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import datetime
import json
from pathlib import Path

from swh.lister.packagist.lister import PackagistLister

_packages_list = {
    "packageNames": [
        "ljjackson/linnworks",
        "lky/wx_article",
        "spryker-eco/computop-api",
        "idevlab/essential",
    ]
}


def _package_metadata(datadir, package_name):
    return json.loads(
        Path(datadir, f"{package_name.replace('/', '_')}.json").read_text()
    )


def _request_without_if_modified_since(request):
    return request.headers.get("If-Modified-Since") is None


def _request_with_if_modified_since(request):
    return request.headers.get("If-Modified-Since") is not None


def test_packagist_lister(swh_scheduler, requests_mock, datadir, requests_mock_datadir):
    # first listing, should return one origin per package
    lister = PackagistLister(scheduler=swh_scheduler)
    requests_mock.get(lister.PACKAGIST_PACKAGES_LIST_URL, json=_packages_list)
    packages_metadata = {}
    for package_name in _packages_list["packageNames"]:
        metadata = _package_metadata(datadir, package_name)
        packages_metadata[package_name] = metadata
        requests_mock.get(
            f"{lister.PACKAGIST_REPO_BASE_URL}/{package_name}.json",
            json=metadata,
            additional_matcher=_request_without_if_modified_since,
        )
    stats = lister.run()

    assert stats.pages == 1
    assert stats.origins == len(_packages_list["packageNames"])
    assert lister.updated

    expected_origins = {
        (
            "https://github.com/gitlky/wx_article",  # standard case
            "git",
            datetime.datetime.fromisoformat("2018-08-30T07:37:09+00:00"),
        ),
        (
            "https://github.com/ljjackson/linnworks.git",  # API goes 404
            "git",
            datetime.datetime.fromisoformat("2018-11-01T21:45:50+00:00"),
        ),
        (
            "https://github.com/spryker-eco/computop-api",  # SSH URL in manifest
            "git",
            datetime.datetime.fromisoformat("2020-06-22T15:50:29+00:00"),
        ),
        (
            "git@gitlab.com:idevlab/Essential.git",  # not GitHub
            "git",
            datetime.datetime.fromisoformat("2022-10-12T10:34:29+00:00"),
        ),
    }

    assert expected_origins == {
        (o.url, o.visit_type, o.last_update)
        for o in swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    }

    # second listing, should return 0 origins as no package metadata
    # has been updated since first listing
    lister = PackagistLister(scheduler=swh_scheduler)
    for package_name in _packages_list["packageNames"]:
        requests_mock.get(
            f"{lister.PACKAGIST_REPO_BASE_URL}/{package_name}.json",
            additional_matcher=_request_with_if_modified_since,
            status_code=304,
        )

    assert lister.get_state_from_scheduler().last_listing_date is not None

    stats = lister.run()

    assert stats.pages == 1
    assert stats.origins == 0
    assert lister.updated

    assert expected_origins == {
        (o.url, o.visit_type, o.last_update)
        for o in swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    }


def test_packagist_lister_missing_metadata(swh_scheduler, requests_mock, datadir):
    lister = PackagistLister(scheduler=swh_scheduler)
    requests_mock.get(lister.PACKAGIST_PACKAGES_LIST_URL, json=_packages_list)
    for package_name in _packages_list["packageNames"]:
        requests_mock.get(
            f"{lister.PACKAGIST_REPO_BASE_URL}/{package_name}.json",
            additional_matcher=_request_without_if_modified_since,
            status_code=404,
        )

    stats = lister.run()

    assert stats.pages == 1
    assert stats.origins == 0


def test_packagist_lister_empty_metadata(swh_scheduler, requests_mock, datadir):
    lister = PackagistLister(scheduler=swh_scheduler)
    requests_mock.get(lister.PACKAGIST_PACKAGES_LIST_URL, json=_packages_list)
    for package_name in _packages_list["packageNames"]:
        requests_mock.get(
            f"{lister.PACKAGIST_REPO_BASE_URL}/{package_name}.json",
            additional_matcher=_request_without_if_modified_since,
            json={"packages": {}},
        )

    stats = lister.run()

    assert stats.pages == 1
    assert stats.origins == 0


def test_packagist_lister_package_with_bitbucket_hg_origin(
    swh_scheduler, requests_mock, datadir
):
    package_name = "den1n/contextmenu"
    lister = PackagistLister(scheduler=swh_scheduler)
    requests_mock.get(
        lister.PACKAGIST_PACKAGES_LIST_URL, json={"packageNames": [package_name]}
    )
    requests_mock.get(
        f"{lister.PACKAGIST_REPO_BASE_URL}/{package_name}.json",
        additional_matcher=_request_without_if_modified_since,
        json=_package_metadata(datadir, package_name),
    )

    stats = lister.run()

    assert stats.pages == 1
    assert stats.origins == 0


def test_packagist_lister_package_normalize_github_origin(
    swh_scheduler, requests_mock, datadir, requests_mock_datadir
):
    package_name = "ycms/module-main"
    lister = PackagistLister(scheduler=swh_scheduler)
    requests_mock.get(
        lister.PACKAGIST_PACKAGES_LIST_URL, json={"packageNames": [package_name]}
    )
    requests_mock.get(
        f"{lister.PACKAGIST_REPO_BASE_URL}/{package_name}.json",
        additional_matcher=_request_without_if_modified_since,
        json=_package_metadata(datadir, package_name),
    )

    stats = lister.run()

    assert stats.pages == 1
    assert stats.origins == 1

    expected_origins = {
        (
            "https://github.com/GameCHN/module-main",
            "git",
            datetime.datetime.fromisoformat("2015-08-23T04:42:33+00:00"),
        ),
    }
    assert expected_origins == {
        (o.url, o.visit_type, o.last_update)
        for o in swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    }


def test_lister_from_configfile(swh_scheduler_config, mocker):
    load_from_envvar = mocker.patch("swh.lister.pattern.load_from_envvar")
    load_from_envvar.return_value = {
        "scheduler": {"cls": "local", **swh_scheduler_config},
        "credentials": {},
    }
    lister = PackagistLister.from_configfile()
    assert lister.scheduler is not None
    assert lister.credentials is not None
