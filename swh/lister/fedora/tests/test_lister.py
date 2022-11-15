# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from io import StringIO
from pathlib import Path
from typing import List
from unittest.mock import MagicMock
from urllib.error import HTTPError

import pytest

from swh.lister.fedora.lister import FedoraLister, Release, get_editions
from swh.scheduler.interface import SchedulerInterface


def mock_repomd(datadir, mocker, use_altered_fedora36=False):
    """Mocks the .xml files fetched by repomd for the next lister run"""
    paths = ["repomd26.xml", "primary26.xml.gz", "repomd36.xml", "primary36.xml.gz"]
    if use_altered_fedora36:
        paths[3] = "primary36-altered.xml.gz"

    cm = MagicMock()
    cm.read.side_effect = [
        Path(datadir, "archives.fedoraproject.org", path).read_bytes() for path in paths
    ]
    cm.__enter__.return_value = cm
    mocker.patch("repomd.urllib.request.urlopen").return_value = cm


def rpm_url(release, path):
    return (
        "https://archives.fedoraproject.org/pub/archive/fedora/linux/releases/"
        f"{release}/Everything/source/tree/Packages/{path}"
    )


@pytest.fixture
def pkg_versions():
    return {
        "https://src.fedoraproject.org/rpms/0install": {
            "fedora26/everything/2.11-4": {
                "name": "0install",
                "version": "2.11-4",
                "buildTime": "2017-02-10T04:59:31+00:00",
                "url": rpm_url(26, "0/0install-2.11-4.fc26.src.rpm"),
                "checksums": {
                    # note: we intentionally altered the original
                    # primary26.xml file to test sha1 usage
                    "sha1": "a6fdef5d1026dea208eeeba148f55ac2f545989b",
                },
            }
        },
        "https://src.fedoraproject.org/rpms/0xFFFF": {
            "fedora26/everything/0.3.9-15": {
                "name": "0xFFFF",
                "version": "0.3.9-15",
                "buildTime": "2017-02-10T05:01:53+00:00",
                "url": rpm_url(26, "0/0xFFFF-0.3.9-15.fc26.src.rpm"),
                "checksums": {
                    "sha256": "96f9c163c0402d2b30e5343c8397a6d50e146c85a446804396b119ef9698231f"
                },
            },
            "fedora36/everything/0.9-4": {
                "name": "0xFFFF",
                "version": "0.9-4",
                "buildTime": "2022-01-19T19:13:53+00:00",
                "url": rpm_url(36, "0/0xFFFF-0.9-4.fc36.src.rpm"),
                "checksums": {
                    "sha256": "45eee8d990d502324ae665233c320b8a5469c25d735f1862e094c1878d6ff2cd"
                },
            },
        },
        "https://src.fedoraproject.org/rpms/2ping": {
            "fedora36/everything/4.5.1-2": {
                "name": "2ping",
                "version": "4.5.1-2",
                "buildTime": "2022-01-19T19:12:21+00:00",
                "url": rpm_url(36, "2/2ping-4.5.1-2.fc36.src.rpm"),
                "checksums": {
                    "sha256": "2ce028d944ebea1cab8c6203c9fed882792478b42fc34682b886a9db16e9de28"
                },
            }
        },
    }


def run_lister(
    swh_scheduler: SchedulerInterface,
    releases: List[Release],
    pkg_versions: dict,
    origin_count: int,
    updated: bool = True,
):
    """Runs the lister and tests that the listed origins are correct."""
    lister = FedoraLister(scheduler=swh_scheduler, releases=releases)

    stats = lister.run()
    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    lister_state = lister.get_state_from_scheduler()
    state_pkg_versions = {k.split("/")[-1]: set(v) for k, v in pkg_versions.items()}

    # One edition from each release (we mocked get_editions)
    assert stats.pages == (len(releases) if updated else 0)
    assert stats.origins == origin_count

    assert {
        o.url: o.extra_loader_arguments["packages"] for o in scheduler_origins
    } == pkg_versions

    assert lister_state.package_versions == state_pkg_versions
    assert lister.updated == updated


def test_get_editions():
    assert get_editions(18) == ["Everything", "Fedora"]
    assert get_editions(26) == ["Everything", "Server", "Workstation"]
    assert get_editions(34) == ["Everything", "Server", "Workstation", "Modular"]


@pytest.mark.parametrize("status_code", [400, 404, 500])
def test_fedora_lister_http_error(
    swh_scheduler: SchedulerInterface, mocker: MagicMock, status_code: int
):
    """
    Simulates handling of HTTP Errors while fetching of packages for fedora releases.
    """
    releases = [18]

    is_404 = status_code == 404

    def side_effect(url):
        if is_404:
            raise HTTPError(
                url, status_code, "Not Found", {"content-type": "text/html"}, StringIO()
            )
        else:
            raise HTTPError(
                url,
                status_code,
                "Internal server error",
                {"content-type": "text/html"},
                StringIO(),
            )

    urlopen_patch = mocker.patch("repomd.urllib.request.urlopen")
    urlopen_patch.side_effect = side_effect

    expected_pkgs: dict = {}

    if is_404:
        run_lister(
            swh_scheduler, releases, expected_pkgs, origin_count=0, updated=False
        )
    else:
        with pytest.raises(HTTPError):
            run_lister(
                swh_scheduler, releases, expected_pkgs, origin_count=0, updated=False
            )


def test_full_lister_fedora(
    swh_scheduler: SchedulerInterface,
    mocker: MagicMock,
    datadir: Path,
    pkg_versions: dict,
):
    """
    Simulates a full listing of packages for fedora releases.
    """
    releases = [26, 36]

    get_editions_patch = mocker.patch("swh.lister.fedora.lister.get_editions")
    get_editions_patch.return_value = ["Everything"]

    mock_repomd(datadir, mocker)
    run_lister(swh_scheduler, releases, pkg_versions, origin_count=3)


def test_incremental_lister(
    swh_scheduler: SchedulerInterface,
    mocker: MagicMock,
    datadir: Path,
    pkg_versions: dict,
):
    """
    Simulates an incremental listing of packages for fedora releases.
    """
    releases = [26, 36]

    get_editions_patch = mocker.patch("swh.lister.fedora.lister.get_editions")
    get_editions_patch.return_value = ["Everything"]

    # First run
    mock_repomd(datadir, mocker)
    run_lister(swh_scheduler, releases, pkg_versions, origin_count=3)
    # Second run (no updates)
    mock_repomd(datadir, mocker)
    run_lister(swh_scheduler, releases, pkg_versions, origin_count=0)

    # Use an altered version of primary36.xml in which we updated the version
    # of package 0xFFFF to 0.10:
    mock_repomd(datadir, mocker, use_altered_fedora36=True)
    # Add new version to the set of expected pkg versions:
    pkg_versions["https://src.fedoraproject.org/rpms/0xFFFF"].update(
        {
            "fedora36/everything/0.10-4": {
                "name": "0xFFFF",
                "version": "0.10-4",
                "buildTime": "2022-01-19T19:13:53+00:00",
                "url": rpm_url(36, "0/0xFFFF-0.10-4.fc36.src.rpm"),
                "checksums": {
                    "sha256": "45eee8d990d502324ae665233c320b8a5469c25d735f1862e094c1878d6ff2cd"
                },
            }
        }
    )

    # Third run (0xFFFF in fedora36 editions got updated and it needs to be listed)
    run_lister(swh_scheduler, releases, pkg_versions, origin_count=1)
