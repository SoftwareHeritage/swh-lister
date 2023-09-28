# Copyright (C) 2022-2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from pathlib import Path
from unittest.mock import Mock

import pytest
from requests_mock.mocker import Mocker as RequestsMocker

from swh.lister.bioconductor.lister import BioconductorLister
from swh.scheduler.interface import SchedulerInterface

BIOCONDUCTOR_URL = "https://www.bioconductor.org"


@pytest.fixture
def packages_json1(datadir):
    text = Path(
        datadir, "https_bioconductor.org", "3.17-bioc-packages.json"
    ).read_text()
    return text, {}


@pytest.fixture
def packages_json2(datadir):
    text = Path(
        datadir, "https_bioconductor.org", "3.17-workflows-packages.json"
    ).read_text()
    return text, {}


@pytest.fixture
def packages_txt1(datadir):
    text = Path(datadir, "https_bioconductor.org", "1.17-PACKAGES").read_text()
    return text, {}


@pytest.fixture
def packages_txt2(datadir):
    text = Path(datadir, "https_bioconductor.org", "2.2-PACKAGES").read_text()
    return text, {}


@pytest.fixture(autouse=True)
def mock_release_announcements(datadir, requests_mock):
    text = Path(
        datadir, "https_bioconductor.org", "about", "release-announcements"
    ).read_text()
    requests_mock.get(
        "https://www.bioconductor.org/about/release-announcements",
        text=text,
        headers={},
    )


def test_bioconductor_incremental_listing(
    swh_scheduler, requests_mock, mocker, packages_json1, packages_json2
):
    kwargs = dict()
    lister = BioconductorLister(
        scheduler=swh_scheduler,
        releases=["3.17"],
        categories=["bioc", "workflows"],
        incremental=True,
        **kwargs,
    )
    assert lister.url == BIOCONDUCTOR_URL

    lister.get_origins_from_page: Mock = mocker.spy(lister, "get_origins_from_page")

    for category, packages_json in [
        ("bioc", packages_json1),
        ("workflows", packages_json2),
    ]:
        text, headers = packages_json
        requests_mock.get(
            (
                "https://www.bioconductor.org/packages/"
                f"json/3.17/{category}/packages.json"
            ),
            text=text,
            headers=headers,
        )

    status = lister.run()
    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    lister_state = lister.get_state_from_scheduler()

    assert status.pages == 3  # 2 categories for 3.17 + 1 None page
    # annotation pkg origin is in 2 categories
    # and we collect git origins as well
    assert status.origins == 6

    assert lister.get_origins_from_page.call_count == 3

    assert [o.url for o in scheduler_origins] == [
        "https://git.bioconductor.org/packages/annotation",
        "https://git.bioconductor.org/packages/arrays",
        "https://git.bioconductor.org/packages/variants",
        "https://www.bioconductor.org/packages/annotation",
        "https://www.bioconductor.org/packages/arrays",
        "https://www.bioconductor.org/packages/variants",
    ]

    assert [
        o.extra_loader_arguments["packages"]
        for o in scheduler_origins
        if "packages" in o.extra_loader_arguments
    ] == [
        {
            "3.17/bioc/1.24.1": {
                "package": "annotation",
                "release": "3.17",
                "tar_url": (
                    "https://www.bioconductor.org/packages/3.17/"
                    "bioc/src/contrib/annotation_1.24.1.tar.gz"
                ),
                "version": "1.24.1",
                "category": "bioc",
                "checksums": {"md5": "4cb4db8807acb2e164985636091faa93"},
                "last_update_date": "2023-06-30",
            },
            "3.17/workflows/1.24.1": {
                "package": "annotation",
                "release": "3.17",
                "tar_url": (
                    "https://www.bioconductor.org/packages/3.17/"
                    "workflows/src/contrib/annotation_1.24.1.tar.gz"
                ),
                "version": "1.24.1",
                "category": "workflows",
                "checksums": {"md5": "4cb4db8807acb2e164985636091faa93"},
                "last_update_date": "2023-06-30",
            },
        },
        {
            "3.17/workflows/1.26.0": {
                "package": "arrays",
                "release": "3.17",
                "tar_url": (
                    "https://www.bioconductor.org/packages/3.17/"
                    "workflows/src/contrib/arrays_1.26.0.tar.gz"
                ),
                "version": "1.26.0",
                "category": "workflows",
                "checksums": {"md5": "009ef917ebc047246b8c62c48e02a237"},
                "last_update_date": "2023-04-28",
            }
        },
        {
            "3.17/bioc/1.24.0": {
                "package": "variants",
                "release": "3.17",
                "tar_url": (
                    "https://www.bioconductor.org/packages/3.17/"
                    "bioc/src/contrib/variants_1.24.0.tar.gz"
                ),
                "version": "1.24.0",
                "category": "bioc",
                "checksums": {"md5": "38f2c00b73e1a695f5ef4c9b4a728923"},
                "last_update_date": "2023-04-28",
            }
        },
    ]

    assert lister_state.package_versions == {
        "annotation": {"3.17/workflows/1.24.1", "3.17/bioc/1.24.1"},
        "arrays": {"3.17/workflows/1.26.0"},
        "variants": {"3.17/bioc/1.24.0"},
    }


@pytest.mark.parametrize("status_code", [400, 500, 404])
def test_bioconductor_lister_http_error(
    swh_scheduler: SchedulerInterface,
    requests_mock: RequestsMocker,
    packages_json1,
    status_code: int,
):
    """
    Simulates handling of HTTP Errors while fetching of packages for bioconductor releases.
    """
    releases = ["3.8"]
    categories = ["workflows", "bioc"]

    requests_mock.get(
        "https://www.bioconductor.org/packages/json/3.8/workflows/packages.json",
        status_code=status_code,
        text="Something went wrong",
    )

    text, headers = packages_json1
    requests_mock.get(
        "https://www.bioconductor.org/packages/json/3.8/bioc/packages.json",
        text=text,
        headers=headers,
    )

    lister = BioconductorLister(
        scheduler=swh_scheduler,
        releases=releases,
        categories=categories,
        incremental=True,
    )

    # On facing HTTP errors, it should continue
    # to crawl other releases/categories
    stats = lister.run()
    # 1 None page + 3.8 bioc page
    assert stats.pages == 2
    # Both packages have git and bioconductor urls.
    assert stats.origins == 4
    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    assert [o.url for o in scheduler_origins] == [
        "https://git.bioconductor.org/packages/annotation",
        "https://git.bioconductor.org/packages/variants",
        "https://www.bioconductor.org/packages/annotation",
        "https://www.bioconductor.org/packages/variants",
    ]
    assert [
        o.extra_loader_arguments["packages"]
        for o in scheduler_origins
        if "packages" in o.extra_loader_arguments
    ] == [
        {
            "3.8/bioc/1.24.1": {
                "package": "annotation",
                "release": "3.8",
                "tar_url": (
                    "https://www.bioconductor.org/packages/"
                    "3.8/bioc/src/contrib/annotation_1.24.1.tar.gz"
                ),
                "version": "1.24.1",
                "category": "bioc",
                "checksums": {"md5": "4cb4db8807acb2e164985636091faa93"},
                "last_update_date": "2023-06-30",
            }
        },
        {
            "3.8/bioc/1.24.0": {
                "package": "variants",
                "release": "3.8",
                "tar_url": (
                    "https://www.bioconductor.org/packages/"
                    "3.8/bioc/src/contrib/variants_1.24.0.tar.gz"
                ),
                "version": "1.24.0",
                "category": "bioc",
                "checksums": {"md5": "38f2c00b73e1a695f5ef4c9b4a728923"},
                "last_update_date": "2023-04-28",
            }
        },
    ]

    lister_state = lister.get_state_from_scheduler()
    assert lister_state.package_versions == {
        "annotation": {"3.8/bioc/1.24.1"},
        "variants": {"3.8/bioc/1.24.0"},
    }


def test_bioconductor_fetch_versions(swh_scheduler: SchedulerInterface):
    lister = BioconductorLister(scheduler=swh_scheduler)
    assert lister.releases == [
        "1.5",
        "1.6",
        "1.7",
        "1.8",
        "1.9",
        "2.0",
        "2.1",
        "2.2",
        "2.3",
        "2.4",
        "2.5",
        "2.6",
        "2.7",
        "2.8",
        "2.9",
        "2.10",
        "2.11",
        "2.12",
        "2.13",
        "2.14",
        "3.0",
        "3.1",
        "3.2",
        "3.3",
        "3.4",
        "3.5",
        "3.6",
        "3.7",
        "3.8",
        "3.9",
        "3.10",
        "3.11",
        "3.12",
        "3.13",
        "3.14",
        "3.15",
        "3.16",
        "3.17",
    ]


def test_bioconductor_lister_parse_packages_txt(
    swh_scheduler: SchedulerInterface, packages_json1, packages_txt1
):
    lister = BioconductorLister(
        scheduler=swh_scheduler, releases=["3.8"], categories=["bioc"]
    )

    text, _ = packages_json1
    res = lister.parse_packages(text)
    assert {
        pkg_name: pkg_metadata["Version"] for pkg_name, pkg_metadata in res.items()
    } == {"annotation": "1.24.1", "maEndToEnd": "2.20.0", "variants": "1.24.0"}

    text, _ = packages_txt1

    res = lister.parse_packages(text)
    assert res == {
        "affylmGUI": {
            "Package": "affylmGUI",
            "Version": "1.4.0",
            "Depends": "limma, tcltk, affy",
            "Suggests": "tkrplot, affyPLM, R2HTML, xtable",
        },
        "affypdnn": {
            "Package": "affypdnn",
            "Version": "1.4.0",
            "Depends": "R (>= 1.9.0), affy (>= 1.5), affydata, hgu95av2probe",
        },
        "affyPLM": {
            "Package": "affyPLM",
            "Version": "1.6.0",
            "Depends": (
                "R (>= 2.0.0), affy (>= 1.5.0), affydata, "
                "Biobase, methods,\n        gcrma"
            ),
        },
    }


def test_bioconductor_lister_old_releases(
    swh_scheduler, mocker, requests_mock, packages_txt1, packages_txt2
):
    releases = ["1.7"]
    categories = ["workflows", "bioc"]

    text, headers = packages_txt1
    requests_mock.get(
        ("https://www.bioconductor.org/packages/" "bioc/1.7/src/contrib/PACKAGES"),
        text=text,
        headers=headers,
    )

    text, headers = packages_txt2
    requests_mock.get(
        "/packages/2.2/bioc/src/contrib/PACKAGES",
        text=text,
        headers=headers,
    )

    requests_mock.get(
        "/packages/2.2/data/experiment/src/contrib/PACKAGES", status_code=404
    )
    requests_mock.get(
        "/packages/2.2/data/annotation/src/contrib/PACKAGES", status_code=404
    )

    lister = BioconductorLister(
        scheduler=swh_scheduler,
        releases=releases,
        categories=categories,
        incremental=True,
    )

    lister.get_origins_from_page: Mock = mocker.spy(lister, "get_origins_from_page")

    stats = lister.run()
    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    lister_state = lister.get_state_from_scheduler()

    assert stats.pages == 2  # 1.7 'bioc' + None page
    assert stats.origins == 3

    assert lister.get_origins_from_page.call_count == 2

    expected_origins = [
        "https://www.bioconductor.org/packages/affyPLM",
        "https://www.bioconductor.org/packages/affylmGUI",
        "https://www.bioconductor.org/packages/affypdnn",
    ]

    assert [o.url for o in scheduler_origins] == expected_origins

    expected_loader_packages = [
        {
            "1.7/bioc/1.6.0": {
                "package": "affyPLM",
                "release": "1.7",
                "tar_url": (
                    "https://www.bioconductor.org/packages/"
                    "bioc/1.7/src/contrib/Source/affyPLM_1.6.0.tar.gz"
                ),
                "version": "1.6.0",
                "category": "bioc",
            }
        },
        {
            "1.7/bioc/1.4.0": {
                "package": "affylmGUI",
                "release": "1.7",
                "tar_url": (
                    "https://www.bioconductor.org/packages/"
                    "bioc/1.7/src/contrib/Source/affylmGUI_1.4.0.tar.gz"
                ),
                "version": "1.4.0",
                "category": "bioc",
            }
        },
        {
            "1.7/bioc/1.4.0": {
                "package": "affypdnn",
                "release": "1.7",
                "tar_url": (
                    "https://www.bioconductor.org/packages/"
                    "bioc/1.7/src/contrib/Source/affypdnn_1.4.0.tar.gz"
                ),
                "version": "1.4.0",
                "category": "bioc",
            }
        },
    ]

    assert [
        o.extra_loader_arguments["packages"] for o in scheduler_origins
    ] == expected_loader_packages

    assert lister_state.package_versions == {
        "affyPLM": {"1.7/bioc/1.6.0"},
        "affylmGUI": {"1.7/bioc/1.4.0"},
        "affypdnn": {"1.7/bioc/1.4.0"},
    }

    releases.append("2.2")

    lister = BioconductorLister(
        scheduler=swh_scheduler, releases=releases, categories=categories
    )

    stats = lister.run()
    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    lister_state = lister.get_state_from_scheduler()

    expected_origins = [
        "https://www.bioconductor.org/packages/ABarray",
        "https://www.bioconductor.org/packages/AnnotationDbi",
    ] + expected_origins

    assert [o.url for o in scheduler_origins] == expected_origins

    expected_loader_packages = [
        {
            "2.2/bioc/1.8.0": {
                "package": "ABarray",
                "release": "2.2",
                "tar_url": (
                    "https://www.bioconductor.org/packages/"
                    "2.2/bioc/src/contrib/ABarray_1.8.0.tar.gz"
                ),
                "version": "1.8.0",
                "category": "bioc",
            }
        },
        {
            "2.2/bioc/1.2.2": {
                "package": "AnnotationDbi",
                "release": "2.2",
                "tar_url": (
                    "https://www.bioconductor.org/packages/"
                    "2.2/bioc/src/contrib/AnnotationDbi_1.2.2.tar.gz"
                ),
                "version": "1.2.2",
                "category": "bioc",
            }
        },
    ] + expected_loader_packages

    assert [
        o.extra_loader_arguments["packages"] for o in scheduler_origins
    ] == expected_loader_packages

    assert lister_state.package_versions == {
        "affyPLM": {"1.7/bioc/1.6.0"},
        "affypdnn": {"1.7/bioc/1.4.0"},
        "affylmGUI": {"1.7/bioc/1.4.0"},
    }
