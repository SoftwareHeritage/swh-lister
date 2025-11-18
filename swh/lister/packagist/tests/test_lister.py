# Copyright (C) 2019-2025  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from swh.lister.packagist.lister import PackagistLister

_packages_list = {
    "packageNames": [
        "ljjackson/linnworks",
        "lky/wx_article",
        "spryker-eco/computop-api",
        "idevlab/essential",  # Git SSH URL
        "payrix/payrix-php",
        "with/invalid_url",  # invalid URL
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
        package_url_format = lister.PACKAGIST_PACKAGE_URL_FORMATS[0]
        package_metadata_url = package_url_format.format(package_name=package_name)
        requests_mock.get(
            package_metadata_url,
            json=metadata,
            additional_matcher=_request_without_if_modified_since,
        )
    stats = lister.run()

    assert stats.pages == 1
    assert stats.origins == len(_packages_list["packageNames"]) - 2
    assert lister.updated

    expected_origins = {
        (
            "https://github.com/gitlky/wx_article",  # standard case
            "git",
            datetime.fromisoformat("2018-08-30T07:37:09+00:00"),
        ),
        (
            "https://github.com/ljjackson/linnworks.git",  # API goes 404
            "git",
            datetime.fromisoformat("2018-10-22T19:52:25+00:00"),
        ),
        (
            "https://github.com/spryker-eco/computop-api",  # SSH URL in manifest
            "git",
            datetime.fromisoformat("2020-06-22T15:50:29+00:00"),
        ),
        (
            "https://gitlab.com/payrix/public/payrix-php.git",  # not GitHub
            "git",
            datetime.fromisoformat("2021-05-25T14:12:28+00:00"),
        ),
    }

    assert expected_origins == {
        (o.url, o.visit_type, o.last_update)
        for o in swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    }

    # second listing, should return 1 origins as no package metadata
    # has been updated since first listing except for the first package
    lister = PackagistLister(scheduler=swh_scheduler)
    for i, package_name in enumerate(_packages_list["packageNames"]):
        package_url_format = lister.PACKAGIST_PACKAGE_URL_FORMATS[0]
        package_metadata_url = package_url_format.format(package_name=package_name)
        if i == 0:
            # Simulate update on first package by setting a last-modified date
            # greater than the last listing date
            requests_mock.head(
                package_metadata_url,
                additional_matcher=_request_with_if_modified_since,
                status_code=200,
                headers={
                    "Last-Modified": (
                        datetime.now(tz=timezone.utc) + timedelta(minutes=1)
                    ).strftime("%a, %d %b %Y %H:%M:%S GMT")
                },
            )
            requests_mock.get(
                package_metadata_url,
                json=_package_metadata(datadir, package_name),
                additional_matcher=_request_with_if_modified_since,
            )
        elif i % 2 == 0:
            # response is a 304 if "If-Modified-Since" request header equals "Last-Modified"
            # response one (really unlikely with lister implementation)
            requests_mock.head(
                package_metadata_url,
                additional_matcher=_request_with_if_modified_since,
                status_code=304,
            )
        else:
            # response is a 200 if "If-Modified-Since" request header does not equal
            # "Last-Modified" response one (happens most of the time with lister
            # implementation)
            requests_mock.head(
                package_metadata_url,
                additional_matcher=_request_with_if_modified_since,
                status_code=200,
                # ensure a last-modified date anterior to current date
                headers={"Last-Modified": "Mon, 15 Apr 2024 07:15:38 GMT"},
            )

    assert lister.get_state_from_scheduler().last_listing_date is not None

    stats = lister.run()

    assert stats.pages == 1
    assert stats.origins == 1
    assert lister.updated

    assert expected_origins == {
        (o.url, o.visit_type, o.last_update)
        for o in swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    }


def test_packagist_lister_missing_metadata(swh_scheduler, requests_mock, datadir):
    lister = PackagistLister(scheduler=swh_scheduler)
    requests_mock.get(lister.PACKAGIST_PACKAGES_LIST_URL, json=_packages_list)
    for package_name in _packages_list["packageNames"]:
        for format_url in lister.PACKAGIST_PACKAGE_URL_FORMATS:
            url = format_url.format(package_name=package_name)
            requests_mock.get(
                url,
                additional_matcher=_request_without_if_modified_since,
                status_code=404,
            )

    stats = lister.run()

    assert stats.pages == 1
    assert stats.origins == 0


def test_packagist_lister_missing_source_metadata(
    swh_scheduler, requests_mock, datadir
):
    lister = PackagistLister(scheduler=swh_scheduler)
    package_name = "ljjackson/linnworks"
    requests_mock.get(
        lister.PACKAGIST_PACKAGES_LIST_URL, json={"packageNames": [package_name]}
    )
    for format_url in lister.PACKAGIST_PACKAGE_URL_FORMATS:
        url = format_url.format(package_name=package_name)
        metadata = _package_metadata(datadir, package_name)
        metadata["packages"][package_name][0]["source"] = None
        requests_mock.get(
            url,
            additional_matcher=_request_without_if_modified_since,
            status_code=200,
            json=metadata,
        )

    stats = lister.run()

    assert stats.pages == 1
    assert stats.origins == 0


def test_packagist_lister_empty_metadata(swh_scheduler, requests_mock, datadir):
    lister = PackagistLister(scheduler=swh_scheduler)
    requests_mock.get(lister.PACKAGIST_PACKAGES_LIST_URL, json=_packages_list)
    for package_name in _packages_list["packageNames"]:
        for format_url in lister.PACKAGIST_PACKAGE_URL_FORMATS:
            url = format_url.format(package_name=package_name)
            requests_mock.get(
                url,
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
    url_not_found = lister.PACKAGIST_PACKAGE_URL_FORMATS[0].format(
        package_name=package_name
    )
    requests_mock.get(
        url_not_found,
        additional_matcher=_request_without_if_modified_since,
        status_code=404,
    )
    url_with_results = lister.PACKAGIST_PACKAGE_URL_FORMATS[1].format(
        package_name=package_name
    )
    requests_mock.get(
        url_with_results,
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
    url_with_results = lister.PACKAGIST_PACKAGE_URL_FORMATS[0].format(
        package_name=package_name
    )
    requests_mock.get(
        url_with_results,
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
            datetime.fromisoformat("2015-08-23T04:42:33+00:00"),
        ),
    }
    assert expected_origins == {
        (o.url, o.visit_type, o.last_update)
        for o in swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    }


def test_lister_from_configfile(swh_scheduler_config, mocker):
    load_from_envvar = mocker.patch("swh.lister.pattern.load_from_envvar")
    load_from_envvar.return_value = {
        "scheduler": {"cls": "postgresql", **swh_scheduler_config},
        "credentials": {},
    }
    lister = PackagistLister.from_configfile()
    assert lister.scheduler is not None
    assert lister.credentials is not None
