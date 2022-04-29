# Copyright (C) 2021-2022 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from pathlib import Path

import iso8601
import pytest
import requests

from swh.lister.maven.lister import MavenLister

MVN_URL = "https://repo1.maven.org/maven2/"  # main maven repo url
INDEX_URL = "http://indexes/export.fld"  # index directory url

URL_POM_1 = MVN_URL + "al/aldi/sprova4j/0.1.0/sprova4j-0.1.0.pom"
URL_POM_2 = MVN_URL + "al/aldi/sprova4j/0.1.1/sprova4j-0.1.1.pom"
URL_POM_3 = MVN_URL + "com/arangodb/arangodb-graphql/1.2/arangodb-graphql-1.2.pom"

LIST_GIT = (
    "git://github.com/aldialimucaj/sprova4j.git",
    "https://github.com/aldialimucaj/sprova4j.git",
)

LIST_GIT_INCR = ("git://github.com/ArangoDB-Community/arangodb-graphql-java.git",)

LIST_SRC = (MVN_URL + "al/aldi/sprova4j",)

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
def maven_index_full(datadir) -> str:
    return Path(datadir, "http_indexes", "export_full.fld").read_text()


@pytest.fixture
def maven_index_incr_first(datadir) -> str:
    return Path(datadir, "http_indexes", "export_incr_first.fld").read_text()


@pytest.fixture
def maven_pom_1(datadir) -> str:
    return Path(datadir, "https_maven.org", "sprova4j-0.1.0.pom").read_text()


@pytest.fixture
def maven_index_null_mtime(datadir) -> str:
    return Path(datadir, "http_indexes", "export_null_mtime.fld").read_text()


@pytest.fixture
def maven_pom_1_malformed(datadir) -> str:
    return Path(datadir, "https_maven.org", "sprova4j-0.1.0.malformed.pom").read_text()


@pytest.fixture
def maven_pom_2(datadir) -> str:
    return Path(datadir, "https_maven.org", "sprova4j-0.1.1.pom").read_text()


@pytest.fixture
def maven_pom_3(datadir) -> str:
    return Path(datadir, "https_maven.org", "arangodb-graphql-1.2.pom").read_text()


@pytest.fixture(autouse=True)
def network_requests_mock(
    requests_mock, maven_index_full, maven_pom_1, maven_pom_2, maven_pom_3
):
    requests_mock.get(INDEX_URL, text=maven_index_full)
    requests_mock.get(URL_POM_1, text=maven_pom_1)
    requests_mock.get(URL_POM_2, text=maven_pom_2)
    requests_mock.get(URL_POM_3, text=maven_pom_3)


def test_maven_full_listing(swh_scheduler):
    """Covers full listing of multiple pages, checking page results and listed
    origins, statelessness."""

    # Run the lister.
    lister = MavenLister(
        scheduler=swh_scheduler,
        url=MVN_URL,
        instance="maven.org",
        index_url=INDEX_URL,
        incremental=False,
    )

    stats = lister.run()

    # Start test checks.
    assert stats.pages == 5

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    origin_urls = [origin.url for origin in scheduler_origins]

    # 3 git origins + 1 maven origin with 2 releases (one per jar)
    assert len(origin_urls) == 4
    assert sorted(origin_urls) == sorted(LIST_GIT + LIST_GIT_INCR + LIST_SRC)

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
    requests_mock,
    maven_pom_1_malformed,
):
    """Covers full listing of multiple pages, checking page results with a malformed
    scm entry in pom."""

    lister = MavenLister(
        scheduler=swh_scheduler,
        url=MVN_URL,
        instance="maven.org",
        index_url=INDEX_URL,
        incremental=False,
    )

    # Set up test.
    requests_mock.get(URL_POM_1, text=maven_pom_1_malformed)

    # Then run the lister.
    stats = lister.run()

    # Start test checks.
    assert stats.pages == 5

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    origin_urls = [origin.url for origin in scheduler_origins]

    # 2 git origins + 1 maven origin with 2 releases (one per jar)
    assert len(origin_urls) == 3
    assert sorted(origin_urls) == sorted((LIST_GIT[1],) + LIST_GIT_INCR + LIST_SRC)

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
    requests_mock,
    maven_index_full,
    maven_index_incr_first,
):
    """Covers full listing of multiple pages, checking page results and listed
    origins, with a second updated run for statefulness."""

    lister = MavenLister(
        scheduler=swh_scheduler,
        url=MVN_URL,
        instance="maven.org",
        index_url=INDEX_URL,
        incremental=True,
    )

    # Set up test.
    requests_mock.get(INDEX_URL, text=maven_index_incr_first)

    # Then run the lister.
    stats = lister.run()

    # Start test checks.
    assert lister.incremental
    assert lister.updated
    assert stats.pages == 2

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    origin_urls = [origin.url for origin in scheduler_origins]

    # 1 git origins + 1 maven origin with 1 release (one per jar)
    assert len(origin_urls) == 2
    assert sorted(origin_urls) == sorted((LIST_GIT[0],) + LIST_SRC)

    for origin in scheduler_origins:
        if origin.visit_type == "maven":
            last_update_src = iso8601.parse_date(LIST_SRC_DATA[0]["time"])
            assert last_update_src == origin.last_update
            assert origin.extra_loader_arguments["artifacts"] == [LIST_SRC_DATA[0]]

    # Second execution of the lister, incremental mode
    lister = MavenLister(
        scheduler=swh_scheduler,
        url=MVN_URL,
        instance="maven.org",
        index_url=INDEX_URL,
        incremental=True,
    )

    scheduler_state = lister.get_state_from_scheduler()
    assert scheduler_state is not None
    assert scheduler_state.last_seen_doc == 1
    assert scheduler_state.last_seen_pom == 1

    # Set up test.
    requests_mock.get(INDEX_URL, text=maven_index_full)

    # Then run the lister.
    stats = lister.run()

    # Start test checks.
    assert lister.incremental
    assert lister.updated
    assert stats.pages == 4

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    origin_urls = [origin.url for origin in scheduler_origins]

    assert sorted(origin_urls) == sorted(LIST_SRC + LIST_GIT + LIST_GIT_INCR)

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


@pytest.mark.parametrize("http_code", [400, 404, 500, 502])
def test_maven_list_http_error_on_index_read(swh_scheduler, requests_mock, http_code):
    """should stop listing if the lister fails to retrieve the main index url."""

    lister = MavenLister(scheduler=swh_scheduler, url=MVN_URL, index_url=INDEX_URL)
    requests_mock.get(INDEX_URL, status_code=http_code)
    with pytest.raises(requests.HTTPError):  # listing cannot continues so stop
        lister.run()

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    assert len(scheduler_origins) == 0


@pytest.mark.parametrize("http_code", [400, 404, 500, 502])
def test_maven_list_http_error_artifacts(
    swh_scheduler,
    requests_mock,
    http_code,
):
    """should continue listing when failing to retrieve artifacts."""
    # Test failure of artefacts retrieval.
    requests_mock.get(URL_POM_1, status_code=http_code)

    lister = MavenLister(scheduler=swh_scheduler, url=MVN_URL, index_url=INDEX_URL)

    # on artifacts though, that raises but continue listing
    lister.run()

    # If the maven_index_full step succeeded but not the get_pom step,
    # then we get only one maven-jar origin and one git origin.
    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    assert len(scheduler_origins) == 3


def test_maven_lister_null_mtime(swh_scheduler, requests_mock, maven_index_null_mtime):

    requests_mock.get(INDEX_URL, text=maven_index_null_mtime)

    # Run the lister.
    lister = MavenLister(
        scheduler=swh_scheduler,
        url=MVN_URL,
        instance="maven.org",
        index_url=INDEX_URL,
        incremental=False,
    )

    stats = lister.run()

    # Start test checks.
    assert stats.pages == 1
    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    assert len(scheduler_origins) == 1
    assert scheduler_origins[0].last_update is None
