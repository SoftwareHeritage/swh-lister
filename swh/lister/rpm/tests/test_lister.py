# Copyright (C) 2022-2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from pathlib import Path
from string import Template
from typing import List

import pytest
from urllib3.exceptions import HTTPError

from swh.lister.rpm.lister import Component, Release, RPMLister
from swh.scheduler.interface import SchedulerInterface

FEDORA_URL = "https://fedoraproject.org/"
FEDORA_ARCHIVE_URL = "https://archives.fedoraproject.org/pub/archive/fedora/linux"

FEDORA_INDEX_URL_TEMPLATES = [
    "$base_url/releases/$release/$component/source/tree/",
    "$base_url/updates/$release/$component/source/tree/",
    "$base_url/releases/$release/$component/source/SRPMS/",
    "$base_url/updates/$release/SRPMS/",
]


def mock_repomd(mocker, side_effect):
    """Mocks the .xml files fetched by repomd for the next lister run"""
    cm = mocker.MagicMock()
    cm.read.side_effect = side_effect
    cm.__enter__.return_value = cm
    mocker.patch("repomd.urllib.request.urlopen").return_value = cm


def mock_fedora_repomd(datadir, mocker, use_altered_fedora36=False):
    repodata = [
        ["repomd26.xml", "primary26.xml.gz"],
        ["repomd36.xml", "primary36.xml.gz"],
    ]
    if use_altered_fedora36:
        repodata[1][1] = "primary36-altered.xml.gz"

    side_effect = []

    for paths in repodata:
        side_effect += [
            Path(datadir, "archives.fedoraproject.org", path).read_bytes()
            for path in paths
        ]
        side_effect += [HTTPError() for _ in range(len(FEDORA_INDEX_URL_TEMPLATES) - 1)]

    mock_repomd(mocker, side_effect)


def rpm_repodata_url(release, component):
    return Template(FEDORA_INDEX_URL_TEMPLATES[0]).substitute(
        base_url=FEDORA_ARCHIVE_URL, release=release, component=component
    )


def rpm_src_package_url(release, component, path):
    return f"{rpm_repodata_url(release, component)}Packages/{path}"


def rpm_package_origin_url(package_name, instance="Fedora"):
    return f"rpm://{instance}/packages/{package_name}"


@pytest.fixture
def pkg_versions():
    return {
        f"{rpm_package_origin_url('0install')}": {
            "26/Everything/2.11-4": {
                "name": "0install",
                "version": "2.11-4",
                "build_time": "2017-02-10T04:59:31+00:00",
                "url": rpm_src_package_url(
                    release="26",
                    component="Everything",
                    path="0/0install-2.11-4.fc26.src.rpm",
                ),
                "checksums": {
                    # note: we intentionally altered the original
                    # primary26.xml file to test sha1 usage
                    "sha1": "a6fdef5d1026dea208eeeba148f55ac2f545989b",
                },
            }
        },
        f"{rpm_package_origin_url('0xFFFF')}": {
            "26/Everything/0.3.9-15": {
                "name": "0xFFFF",
                "version": "0.3.9-15",
                "build_time": "2017-02-10T05:01:53+00:00",
                "url": rpm_src_package_url(
                    release="26",
                    component="Everything",
                    path="0/0xFFFF-0.3.9-15.fc26.src.rpm",
                ),
                "checksums": {
                    "sha256": "96f9c163c0402d2b30e5343c8397a6d50e146c85a446804396b119ef9698231f"
                },
            },
            "36/Everything/0.9-4": {
                "name": "0xFFFF",
                "version": "0.9-4",
                "build_time": "2022-01-19T19:13:53+00:00",
                "url": rpm_src_package_url(
                    release="36",
                    component="Everything",
                    path="0/0xFFFF-0.9-4.fc36.src.rpm",
                ),
                "checksums": {
                    "sha256": "45eee8d990d502324ae665233c320b8a5469c25d735f1862e094c1878d6ff2cd"
                },
            },
        },
        f"{rpm_package_origin_url('2ping')}": {
            "36/Everything/4.5.1-2": {
                "name": "2ping",
                "version": "4.5.1-2",
                "build_time": "2022-01-19T19:12:21+00:00",
                "url": rpm_src_package_url(
                    release="36",
                    component="Everything",
                    path="2/2ping-4.5.1-2.fc36.src.rpm",
                ),
                "checksums": {
                    "sha256": "2ce028d944ebea1cab8c6203c9fed882792478b42fc34682b886a9db16e9de28"
                },
            }
        },
    }


def run_lister(
    swh_scheduler: SchedulerInterface,
    releases: List[Release],
    components: List[Component],
    pkg_versions: dict,
    origin_count: int,
    incremental: bool = False,
    updated: bool = True,
):
    """Runs the lister and tests that the listed origins are correct."""
    lister = RPMLister(
        scheduler=swh_scheduler,
        url=FEDORA_URL,
        instance="Fedora",
        rpm_src_data=[
            {
                "base_url": FEDORA_ARCHIVE_URL,
                "releases": releases,
                "components": components,
                "index_url_templates": FEDORA_INDEX_URL_TEMPLATES,
            }
        ],
        incremental=incremental,
    )

    stats = lister.run()
    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    lister_state = lister.get_state_from_scheduler()
    state_pkg_versions = {k.split("/")[-1]: set(v) for k, v in pkg_versions.items()}

    # One component from each release plus extra null page to flush origins
    assert stats.pages == (len(releases) + 1 if updated else 1)
    assert stats.origins == origin_count

    assert {
        o.url: o.extra_loader_arguments["packages"] for o in scheduler_origins
    } == pkg_versions

    if incremental:
        assert lister_state.package_versions == state_pkg_versions
        assert lister.updated == updated


@pytest.mark.parametrize("status_code", [400, 404, 500])
def test_fedora_lister_http_error(swh_scheduler, mocker, status_code):
    """
    Simulates handling of HTTP Errors while fetching packages for fedora releases.
    """

    release = "18"
    component = "Everything"

    mock_repomd(
        mocker,
        side_effect=[HTTPError() for _ in range(len(FEDORA_INDEX_URL_TEMPLATES))],
    )

    run_lister(
        swh_scheduler,
        releases=[release],
        components=[component],
        pkg_versions={},
        origin_count=0,
        updated=False,
    )


def test_full_rpm_lister(
    swh_scheduler,
    mocker,
    datadir,
    pkg_versions,
):
    """
    Simulates a full listing of packages for fedora releases.
    """

    mock_fedora_repomd(datadir, mocker)
    run_lister(
        swh_scheduler,
        releases=["26", "36"],
        components=["Everything"],
        pkg_versions=pkg_versions,
        origin_count=3,
    )


def test_incremental_rpm_lister(
    swh_scheduler,
    mocker,
    datadir,
    pkg_versions,
):
    """
    Simulates an incremental listing of packages for fedora releases.
    """

    # First run
    mock_fedora_repomd(datadir, mocker)
    run_lister(
        swh_scheduler,
        releases=["26", "36"],
        components=["Everything"],
        pkg_versions=pkg_versions,
        origin_count=3,
        incremental=True,
    )
    # Second run (no updates)
    mock_fedora_repomd(datadir, mocker)
    run_lister(
        swh_scheduler,
        releases=["26", "36"],
        components=["Everything"],
        pkg_versions=pkg_versions,
        origin_count=0,
        incremental=True,
    )

    # Use an altered version of primary36.xml in which we updated the version
    # of package 0xFFFF to 0.10:
    mock_fedora_repomd(datadir, mocker, use_altered_fedora36=True)
    # Add new version to the set of expected pkg versions:
    pkg_versions[rpm_package_origin_url("0xFFFF")].update(
        {
            "36/Everything/0.10-4": {
                "name": "0xFFFF",
                "version": "0.10-4",
                "build_time": "2022-01-19T19:13:53+00:00",
                "url": rpm_src_package_url(
                    release="36",
                    component="Everything",
                    path="0/0xFFFF-0.10-4.fc36.src.rpm",
                ),
                "checksums": {
                    "sha256": "45eee8d990d502324ae665233c320b8a5469c25d735f1862e094c1878d6ff2cd"
                },
            }
        }
    )

    # Third run (0xFFFF in fedora36 component got updated and it needs to be listed)
    run_lister(
        swh_scheduler,
        releases=["26", "36"],
        components=["Everything"],
        pkg_versions=pkg_versions,
        origin_count=1,
        incremental=True,
    )
