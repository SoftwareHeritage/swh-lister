# Copyright (C) 2021-2025 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os
from pathlib import Path
import subprocess

import iso8601
import pytest
import requests

from swh.lister.maven.lister import MavenLister

MVN_URL = "https://repo1.maven.org/maven2/"  # main maven repo url

URL_POM_1 = MVN_URL + "al/aldi/sprova4j/0.1.0/sprova4j-0.1.0.pom"
URL_POM_2 = MVN_URL + "al/aldi/sprova4j/0.1.1/sprova4j-0.1.1.pom"
URL_POM_3 = MVN_URL + "com/arangodb/arangodb-graphql/1.2/arangodb-graphql-1.2.pom"


USER_REPO0 = "aldialimucaj/sprova4j"
GIT_REPO_URL0_HTTPS = f"https://github.com/{USER_REPO0}"
GIT_REPO_URL0_API = f"https://api.github.com/repos/{USER_REPO0}"
ORIGIN_GIT = GIT_REPO_URL0_HTTPS

USER_REPO1 = "ArangoDB-Community/arangodb-graphql-java"
GIT_REPO_URL1_HTTPS = f"https://github.com/{USER_REPO1}"
GIT_REPO_URL1_GIT = f"git://github.com/{USER_REPO1}.git"
GIT_REPO_URL1_API = f"https://api.github.com/repos/{USER_REPO1}"
ORIGIN_GIT_INCR = GIT_REPO_URL1_HTTPS

USER_REPO2 = "webx/citrus"
GIT_REPO_URL2_HTTPS = f"https://github.com/{USER_REPO2}"
GIT_REPO_URL2_API = f"https://api.github.com/repos/{USER_REPO2}"

ORIGIN_SRC = MVN_URL + "al/aldi/sprova4j"

LIST_SRC_DATA = (
    {
        "type": "maven",
        "url": "https://repo1.maven.org/maven2/al/aldi/sprova4j"
        + "/0.1.0/sprova4j-0.1.0-sources.jar",
        "time": "2021-07-12T17:06:59+00:00",
        "gid": "al.aldi",
        "aid": "sprova4j",
        "version": "0.1.0",
        "base_url": MVN_URL,
    },
    {
        "type": "maven",
        "url": "https://repo1.maven.org/maven2/al/aldi/sprova4j"
        + "/0.1.1/sprova4j-0.1.1-sources.jar",
        "time": "2021-07-12T17:37:05+00:00",
        "gid": "al.aldi",
        "aid": "sprova4j",
        "version": "0.1.1",
        "base_url": MVN_URL,
    },
)


@pytest.fixture
def maven_index_full_publish_dir(datadir):
    return os.path.join(datadir, "export_full")


@pytest.fixture
def maven_index_incr_first_publish_dir(datadir):
    return os.path.join(datadir, "export_incr_first")


@pytest.fixture
def maven_index_null_mtime_publish_dir(datadir):
    return os.path.join(datadir, "export_null_mtime")


def mock_maven_index_exporter(mocker, publish_dir):
    mocker.patch("tempfile.TemporaryDirectory.__enter__").return_value = publish_dir
    mocker.patch("subprocess.check_call")


@pytest.mark.parametrize("mvn_url", [MVN_URL, MVN_URL.rstrip("/")])
def test_maven_full_listing(
    swh_scheduler, mocker, maven_index_full_publish_dir, mvn_url, requests_mock_datadir
):
    """Covers full listing of multiple pages, checking page results and listed
    origins, statelessness."""

    mock_maven_index_exporter(mocker, maven_index_full_publish_dir)

    # Run the lister.
    lister = MavenLister(
        scheduler=swh_scheduler,
        url=mvn_url,
        instance="maven.org",
        incremental=False,
    )

    stats = lister.run()

    # Start test checks.
    assert stats.pages == 6

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    origin_urls = [origin.url for origin in scheduler_origins]

    # 3 git origins + 1 maven origin with 2 releases (one per jar)
    assert set(origin_urls) == {ORIGIN_GIT, ORIGIN_GIT_INCR, ORIGIN_SRC}
    assert len(set(origin_urls)) == len(origin_urls)

    for origin in scheduler_origins:
        if origin.visit_type == "maven":
            for src in LIST_SRC_DATA:
                last_update_src = iso8601.parse_date(src["time"])
                assert last_update_src <= origin.last_update
            assert origin.extra_loader_arguments["artifacts"] == list(LIST_SRC_DATA)

    scheduler_state = lister.get_state_from_scheduler()
    assert scheduler_state is not None
    assert scheduler_state.last_seen_doc == -1
    assert scheduler_state.last_seen_pom == -1


def test_maven_full_listing_malformed(
    swh_scheduler,
    requests_mock_datadir,
    requests_mock,
    datadir,
    mocker,
    maven_index_full_publish_dir,
):
    """Covers full listing of multiple pages, checking page results with a malformed
    scm entry in pom."""

    mock_maven_index_exporter(mocker, maven_index_full_publish_dir)

    lister = MavenLister(
        scheduler=swh_scheduler,
        url=MVN_URL,
        instance="maven.org",
        incremental=False,
    )

    # Set up test.
    requests_mock.get(
        URL_POM_1, content=Path(datadir, "sprova4j-0.1.0.malformed.pom").read_bytes()
    )

    # Then run the lister.
    stats = lister.run()

    # Start test checks.
    assert stats.origins == 3
    assert stats.pages == 6

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    origin_urls = [origin.url for origin in scheduler_origins]

    # 2 git origins + 1 maven origin with 2 releases (one per jar)
    assert set(origin_urls) == {ORIGIN_GIT, ORIGIN_GIT_INCR, ORIGIN_SRC}
    assert len(origin_urls) == len(set(origin_urls))

    for origin in scheduler_origins:
        if origin.visit_type == "maven":
            for src in LIST_SRC_DATA:
                last_update_src = iso8601.parse_date(src["time"])
                assert last_update_src <= origin.last_update
            assert origin.extra_loader_arguments["artifacts"] == list(LIST_SRC_DATA)

    scheduler_state = lister.get_state_from_scheduler()
    assert scheduler_state is not None
    assert scheduler_state.last_seen_doc == -1
    assert scheduler_state.last_seen_pom == -1


def test_maven_ignore_invalid_url(
    swh_scheduler,
    requests_mock_datadir,
    requests_mock,
    datadir,
    mocker,
    maven_index_full_publish_dir,
):
    """Covers full listing of multiple pages, checking page results with a malformed
    scm entry in pom."""

    mock_maven_index_exporter(mocker, maven_index_full_publish_dir)

    lister = MavenLister(
        scheduler=swh_scheduler,
        url=MVN_URL,
        instance="maven.org",
        incremental=False,
    )

    # Set up test.
    requests_mock.get(
        URL_POM_1, content=Path(datadir, "sprova4j-0.1.0.invalidurl.pom").read_bytes()
    )

    # Then run the lister.
    stats = lister.run()

    # Start test checks.
    assert stats.pages == 6

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    origin_urls = [origin.url for origin in scheduler_origins]

    # 1 git origins (the other ignored) + 1 maven origin with 2 releases (one per jar)
    assert set(origin_urls) == {ORIGIN_GIT_INCR, ORIGIN_SRC}
    assert len(origin_urls) == len(set(origin_urls))

    for origin in scheduler_origins:
        if origin.visit_type == "maven":
            for src in LIST_SRC_DATA:
                last_update_src = iso8601.parse_date(src["time"])
                assert last_update_src <= origin.last_update
            assert origin.extra_loader_arguments["artifacts"] == list(LIST_SRC_DATA)

    scheduler_state = lister.get_state_from_scheduler()
    assert scheduler_state is not None
    assert scheduler_state.last_seen_doc == -1
    assert scheduler_state.last_seen_pom == -1


def test_maven_incremental_listing(
    swh_scheduler,
    requests_mock_datadir,
    mocker,
    maven_index_full_publish_dir,
    maven_index_incr_first_publish_dir,
):
    """Covers full listing of multiple pages, checking page results and listed
    origins, with a second updated run for statefulness."""

    # Setup test
    mock_maven_index_exporter(mocker, maven_index_incr_first_publish_dir)

    lister = MavenLister(
        scheduler=swh_scheduler,
        url=MVN_URL,
        instance="maven.org",
        incremental=True,
    )

    # Then run the lister.
    stats = lister.run()

    # Start test checks.
    assert lister.incremental
    assert lister.updated
    assert stats.pages == 3
    assert stats.origins == 2

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    origin_urls = [origin.url for origin in scheduler_origins]

    # 1 git origins + 1 maven origin with 1 release
    assert set(origin_urls) == {ORIGIN_GIT, ORIGIN_SRC}
    assert len(origin_urls) == len(set(origin_urls))

    for origin in scheduler_origins:
        if origin.visit_type == "maven":
            last_update_src = iso8601.parse_date(LIST_SRC_DATA[0]["time"])
            assert last_update_src == origin.last_update
            assert origin.extra_loader_arguments["artifacts"] == [LIST_SRC_DATA[0]]

    # Setup test
    mock_maven_index_exporter(mocker, maven_index_full_publish_dir)

    # Second execution of the lister, incremental mode
    lister = MavenLister(
        scheduler=swh_scheduler,
        url=MVN_URL,
        instance="maven.org",
        incremental=True,
    )

    scheduler_state = lister.get_state_from_scheduler()
    assert scheduler_state is not None
    assert scheduler_state.last_seen_doc == 1
    assert scheduler_state.last_seen_pom == 1

    # Then run the lister.
    stats = lister.run()

    # Start test checks.
    assert lister.incremental
    assert lister.updated
    assert stats.pages == 5
    assert stats.origins == 2

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    origin_urls = [origin.url for origin in scheduler_origins]

    # 2 git origins + same maven origin as previously but with a new release
    assert set(origin_urls) == {ORIGIN_SRC, ORIGIN_GIT, ORIGIN_GIT_INCR}
    assert len(origin_urls) == len(set(origin_urls))

    for origin in scheduler_origins:
        if origin.visit_type == "maven":
            for src in LIST_SRC_DATA:
                last_update_src = iso8601.parse_date(src["time"])
                assert last_update_src <= origin.last_update
            assert origin.extra_loader_arguments["artifacts"] == list(LIST_SRC_DATA)

    scheduler_state = lister.get_state_from_scheduler()
    assert scheduler_state is not None
    assert scheduler_state.last_seen_doc == 4
    assert scheduler_state.last_seen_pom == 4


def test_maven_list_index_export_error(swh_scheduler, mocker):
    """should stop listing if the maven index exporter tool failed."""

    mocker.patch("subprocess.check_call").side_effect = subprocess.CalledProcessError(
        returncode=1, cmd=["python3", "/opt/maven-index-exporter/run_full_export.py"]
    )

    lister = MavenLister(scheduler=swh_scheduler, url=MVN_URL)
    with pytest.raises(
        subprocess.CalledProcessError
    ):  # listing cannot continues so stop
        lister.run()

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    assert len(scheduler_origins) == 0


@pytest.mark.parametrize("http_code", [400, 404, 500, 502])
def test_maven_list_http_error_artifacts(
    swh_scheduler,
    requests_mock,
    http_code,
    mocker,
    maven_index_full_publish_dir,
    requests_mock_datadir,
):
    """should continue listing when failing to retrieve artifacts."""
    mock_maven_index_exporter(mocker, maven_index_full_publish_dir)
    # Test failure of artefacts retrieval.
    requests_mock.get(URL_POM_1, status_code=http_code)

    lister = MavenLister(scheduler=swh_scheduler, url=MVN_URL)

    # on artifacts though, that raises but continue listing
    lister.run()

    # If the maven_index_full step succeeded but not the get_pom step,
    # then we get only one maven-jar origin and one git origin.
    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    origin_urls = [origin.url for origin in scheduler_origins]

    assert set(origin_urls) == {ORIGIN_SRC, ORIGIN_GIT_INCR}
    assert len(origin_urls) == len(set(origin_urls))


def test_maven_lister_null_mtime(
    swh_scheduler, mocker, maven_index_null_mtime_publish_dir
):
    mock_maven_index_exporter(mocker, maven_index_null_mtime_publish_dir)

    # Run the lister.
    lister = MavenLister(
        scheduler=swh_scheduler,
        url=MVN_URL,
        instance="maven.org",
        incremental=False,
    )

    stats = lister.run()

    # Start test checks.
    assert stats.pages == 2
    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    assert len(scheduler_origins) == 1
    assert scheduler_origins[0].last_update is None


def test_maven_list_pom_bad_encoding(
    swh_scheduler,
    requests_mock_datadir,
    requests_mock,
    mocker,
    maven_index_full_publish_dir,
):
    """should successfully parse a pom file with unexpected encoding
    (beautifulsoup4 >= 4.13)."""
    mock_maven_index_exporter(mocker, maven_index_full_publish_dir)
    # Test pom parsing by reencoding a UTF-8 pom file to a not expected one
    requests_mock.get(
        URL_POM_1,
        content=requests.get(URL_POM_1).content.decode("utf-8").encode("utf-32"),
    )

    lister = MavenLister(scheduler=swh_scheduler, url=MVN_URL)

    lister.run()

    # we should get one maven-jar origin and two git origins.
    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    assert len(scheduler_origins) == 3

    # git origin parsed from pom file with unexpected encoding
    assert ("https://github.com/aldialimucaj/sprova4j", "git") in [
        (o.url, o.visit_type) for o in scheduler_origins
    ]


def test_maven_list_pom_multi_byte_encoding(
    swh_scheduler,
    requests_mock_datadir,
    requests_mock,
    datadir,
    mocker,
    maven_index_full_publish_dir,
):
    """should parse POM file with multi-byte encoding."""

    mock_maven_index_exporter(mocker, maven_index_full_publish_dir)
    # replace pom file with a multi-byte encoding one
    requests_mock.get(
        URL_POM_1, content=Path(datadir, "citrus-parent-3.0.7.pom").read_bytes()
    )

    lister = MavenLister(scheduler=swh_scheduler, url=MVN_URL)

    lister.run()

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    assert len(scheduler_origins) == 3
