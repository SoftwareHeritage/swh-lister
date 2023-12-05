# Copyright (C) 2019-2021 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from collections import defaultdict
from datetime import datetime
from email.utils import formatdate, parsedate_to_datetime
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple

from debian.deb822 import Sources
import pytest

from swh.lister.debian.lister import (
    DebianLister,
    DebianOrigin,
    PkgName,
    PkgVersion,
    Suite,
)
from swh.scheduler.interface import SchedulerInterface

# Those tests use sample debian Sources files whose content has been extracted
# from the real Sources files from stretch, buster and bullseye suite.
# They contain the following package source info
#  - stretch:
#      * dh-elpa (versions: 0.0.18, 0.0.19, 0.0.20),
#      * git (version: 1:2.11.0-3+deb9u7)
#  - buster:
#      * git (version: 1:2.20.1-2+deb10u3),
#      * subversion (version: 1.10.4-1+deb10u1)
#  - bullseye:
#      * git (version: 1:2.29.2-1)
#      * subversion (version: 1.14.0-3)
#      * hg-git (version: 0.9.0-2)

_mirror_url = "http://deb.debian.org/debian"
_suites = ["stretch", "buster", "bullseye"]
_components = ["main", "foo"]
_last_modified = {}

SourcesText = str


def _debian_sources_content(datadir: str, suite: Suite) -> SourcesText:
    return Path(datadir, f"Sources_{suite}").read_text()


@pytest.fixture
def debian_sources(datadir: str) -> Dict[Suite, SourcesText]:
    return {suite: _debian_sources_content(datadir, suite) for suite in _suites}


# suite -> package name -> list of versions
DebianSuitePkgSrcInfo = Dict[Suite, Dict[PkgName, List[Sources]]]


def _init_test(
    swh_scheduler: SchedulerInterface,
    debian_sources: Dict[Suite, SourcesText],
    requests_mock,
) -> Tuple[DebianLister, DebianSuitePkgSrcInfo]:
    lister = DebianLister(
        scheduler=swh_scheduler,
        url=_mirror_url,
        suites=list(debian_sources.keys()),
        components=_components,
    )

    suite_pkg_info: DebianSuitePkgSrcInfo = {}

    for i, (suite, sources) in enumerate(debian_sources.items()):
        # ensure to generate a different date for each suite
        last_modified = formatdate(timeval=datetime.now().timestamp() + i, usegmt=True)
        suite_pkg_info[suite] = defaultdict(list)
        for pkg_src in Sources.iter_paragraphs(sources):
            suite_pkg_info[suite][pkg_src["Package"]].append(pkg_src)
            # backup package last update date
            global _last_modified
            _last_modified[pkg_src["Package"]] = last_modified

        for idx_url, compression in lister.debian_index_urls(suite, _components[0]):
            if compression:
                requests_mock.get(idx_url, status_code=404)
            else:
                requests_mock.get(
                    idx_url,
                    text=sources,
                    headers={"Last-Modified": last_modified},
                )

        for idx_url, _ in lister.debian_index_urls(suite, _components[1]):
            requests_mock.get(idx_url, status_code=404)

    return lister, suite_pkg_info


def _check_listed_origins(
    swh_scheduler: SchedulerInterface,
    lister: DebianLister,
    suite_pkg_info: DebianSuitePkgSrcInfo,
    lister_previous_state: Dict[PkgName, Set[PkgVersion]],
) -> Set[DebianOrigin]:
    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    origin_urls = set()

    # iterate on each debian suite for the main component
    for suite, pkg_info in suite_pkg_info.items():
        # iterate on each package
        for package_name, pkg_srcs in pkg_info.items():
            # iterate on each package version info
            for pkg_src in pkg_srcs:
                # build package version key
                package_version_key = f"{suite}/{_components[0]}/{pkg_src['Version']}"
                # if package or its version not previously listed, those info should
                # have been sent to the scheduler database
                if (
                    package_name not in lister_previous_state
                    or package_version_key not in lister_previous_state[package_name]
                ):
                    # build origin url
                    origin_url = lister.origin_url_for_package(package_name)
                    origin_urls.add(origin_url)
                    # get ListerOrigin object from scheduler database
                    filtered_origins = [
                        scheduler_origin
                        for scheduler_origin in scheduler_origins
                        if scheduler_origin.url == origin_url
                    ]

                    assert filtered_origins
                    expected_last_update = parsedate_to_datetime(
                        _last_modified[pkg_src["Package"]]
                    )
                    assert filtered_origins[0].last_update == expected_last_update
                    packages = filtered_origins[0].extra_loader_arguments["packages"]
                    # check the version info are available
                    assert package_version_key in packages

                    # check package files URIs are available
                    for file in pkg_src["files"]:
                        filename = file["name"]
                        file_uri = os.path.join(
                            _mirror_url, pkg_src["Directory"], filename
                        )
                        package_files = packages[package_version_key]["files"]
                        assert filename in package_files
                        assert package_files[filename]["uri"] == file_uri

                    # check listed package version is in lister state
                    assert package_name in lister.state.package_versions
                    assert (
                        package_version_key
                        in lister.state.package_versions[package_name]
                    )
    return origin_urls


def test_lister_debian_all_suites(
    swh_scheduler: SchedulerInterface,
    debian_sources: Dict[Suite, SourcesText],
    requests_mock,
):
    """
    Simulate a full listing of main component packages for all debian suites.
    """
    lister, suite_pkg_info = _init_test(swh_scheduler, debian_sources, requests_mock)

    stats = lister.run()

    origin_urls = _check_listed_origins(
        swh_scheduler, lister, suite_pkg_info, lister_previous_state={}
    )

    assert stats.pages == len(_suites) * len(_components)
    assert stats.origins == len(origin_urls)

    stats = lister.run()

    assert stats.pages == len(_suites) * len(_components)
    assert stats.origins == 0


@pytest.mark.parametrize(
    "suites_params",
    [
        [_suites[:1]],
        [_suites[:1], _suites[:2]],
        [_suites[:1], _suites[:2], _suites],
    ],
)
def test_lister_debian_updated_packages(
    swh_scheduler: SchedulerInterface,
    debian_sources: Dict[Suite, SourcesText],
    requests_mock,
    suites_params: List[Suite],
):
    """
    Simulate incremental listing of main component packages by adding new suite
    to process between each listing operation.
    """

    lister_previous_state: Dict[PkgName, Set[PkgVersion]] = {}

    for idx, suites in enumerate(suites_params):
        sources = {suite: debian_sources[suite] for suite in suites}

        lister, suite_pkg_info = _init_test(swh_scheduler, sources, requests_mock)

        stats = lister.run()

        origin_urls = _check_listed_origins(
            swh_scheduler,
            lister,
            suite_pkg_info,
            lister_previous_state=lister_previous_state,
        )

        assert stats.pages == len(sources) * len(_components)
        assert stats.origins == len(origin_urls)

        lister_previous_state = lister.state.package_versions

        # only new packages or packages with new versions should be listed
        if len(suites) > 1 and idx < len(suites) - 1:
            assert stats.origins == 0
        else:
            assert stats.origins != 0


@pytest.mark.parametrize(
    "credentials, expected_credentials",
    [
        (None, []),
        ({"key": "value"}, []),
        (
            {"debian": {"Debian": [{"username": "user", "password": "pass"}]}},
            [{"username": "user", "password": "pass"}],
        ),
    ],
)
def test_lister_debian_instantiation_with_credentials(
    credentials, expected_credentials, swh_scheduler
):
    lister = DebianLister(swh_scheduler, credentials=credentials)

    # Credentials are allowed in constructor
    assert lister.credentials == expected_credentials


def test_lister_debian_from_configfile(swh_scheduler_config, mocker):
    load_from_envvar = mocker.patch("swh.lister.pattern.load_from_envvar")
    load_from_envvar.return_value = {
        "scheduler": {"cls": "local", **swh_scheduler_config},
        "credentials": {},
    }
    lister = DebianLister.from_configfile()
    assert lister.scheduler is not None
    assert lister.credentials is not None
