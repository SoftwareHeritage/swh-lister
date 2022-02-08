# Copyright (C) 2021 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from datetime import timezone
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

LIST_SRC = (
    MVN_URL + "al/aldi/sprova4j/0.1.0/sprova4j-0.1.0-sources.jar",
    MVN_URL + "al/aldi/sprova4j/0.1.1/sprova4j-0.1.1-sources.jar",
)

LIST_SRC_DATA = (
    {
        "type": "maven",
        "url": "https://repo1.maven.org/maven2/al/aldi/sprova4j"
        + "/0.1.0/sprova4j-0.1.0-sources.jar",
        "time": "2021-07-12T17:06:59+00:00",
        "gid": "al.aldi",
        "aid": "sprova4j",
        "version": "0.1.0",
    },
    {
        "type": "maven",
        "url": "https://repo1.maven.org/maven2/al/aldi/sprova4j"
        + "/0.1.1/sprova4j-0.1.1-sources.jar",
        "time": "2021-07-12T17:37:05+00:00",
        "gid": "al.aldi",
        "aid": "sprova4j",
        "version": "0.1.1",
    },
)


@pytest.fixture
def maven_index(datadir) -> str:
    return Path(datadir, "http_indexes", "export.fld").read_text()


@pytest.fixture
def maven_index_incr(datadir) -> str:
    return Path(datadir, "http_indexes", "export_incr.fld").read_text()


@pytest.fixture
def maven_pom_1(datadir) -> str:
    return Path(datadir, "https_maven.org", "sprova4j-0.1.0.pom").read_text()


@pytest.fixture
def maven_pom_1_malformed(datadir) -> str:
    return Path(datadir, "https_maven.org", "sprova4j-0.1.0.malformed.pom").read_text()


@pytest.fixture
def maven_pom_2(datadir) -> str:
    return Path(datadir, "https_maven.org", "sprova4j-0.1.1.pom").read_text()


@pytest.fixture
def maven_pom_3(datadir) -> str:
    return Path(datadir, "https_maven.org", "arangodb-graphql-1.2.pom").read_text()


def test_maven_full_listing(
    swh_scheduler, requests_mock, mocker, maven_index, maven_pom_1, maven_pom_2,
):
    """Covers full listing of multiple pages, checking page results and listed
    origins, statelessness."""

    lister = MavenLister(
        scheduler=swh_scheduler,
        url=MVN_URL,
        instance="maven.org",
        index_url=INDEX_URL,
        incremental=False,
    )

    # Set up test.
    index_text = maven_index
    requests_mock.get(INDEX_URL, text=index_text)
    requests_mock.get(URL_POM_1, text=maven_pom_1)
    requests_mock.get(URL_POM_2, text=maven_pom_2)

    # Then run the lister.
    stats = lister.run()

    # Start test checks.
    assert stats.pages == 4
    assert stats.origins == 4

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    origin_urls = [origin.url for origin in scheduler_origins]
    assert sorted(origin_urls) == sorted(LIST_GIT + LIST_SRC)

    for origin in scheduler_origins:
        if origin.visit_type == "maven":
            for src in LIST_SRC_DATA:
                if src.get("url") == origin.url:
                    last_update_src = iso8601.parse_date(src.get("time")).astimezone(
                        tz=timezone.utc
                    )
                    assert last_update_src == origin.last_update
                    artifact = origin.extra_loader_arguments["artifacts"][0]
                    assert src.get("time") == artifact["time"]
                    assert src.get("gid") == artifact["gid"]
                    assert src.get("aid") == artifact["aid"]
                    assert src.get("version") == artifact["version"]
                    assert MVN_URL == artifact["base_url"]
                    break
            else:
                raise AssertionError(
                    "Could not find scheduler origin in referenced origins."
                )
    scheduler_state = lister.get_state_from_scheduler()
    assert scheduler_state is not None
    assert scheduler_state.last_seen_doc == -1
    assert scheduler_state.last_seen_pom == -1


def test_maven_full_listing_malformed(
    swh_scheduler,
    requests_mock,
    mocker,
    maven_index,
    maven_pom_1_malformed,
    maven_pom_2,
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
    index_text = maven_index
    requests_mock.get(INDEX_URL, text=index_text)
    requests_mock.get(URL_POM_1, text=maven_pom_1_malformed)
    requests_mock.get(URL_POM_2, text=maven_pom_2)

    # Then run the lister.
    stats = lister.run()

    # Start test checks.
    assert stats.pages == 4
    assert stats.origins == 3

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    origin_urls = [origin.url for origin in scheduler_origins]
    LIST_SRC_1 = ("https://github.com/aldialimucaj/sprova4j.git",)
    assert sorted(origin_urls) == sorted(LIST_SRC_1 + LIST_SRC)

    for origin in scheduler_origins:
        if origin.visit_type == "maven":
            for src in LIST_SRC_DATA:
                if src.get("url") == origin.url:
                    artifact = origin.extra_loader_arguments["artifacts"][0]
                    assert src.get("time") == artifact["time"]
                    assert src.get("gid") == artifact["gid"]
                    assert src.get("aid") == artifact["aid"]
                    assert src.get("version") == artifact["version"]
                    assert MVN_URL == artifact["base_url"]
                    break
            else:
                raise AssertionError(
                    "Could not find scheduler origin in referenced origins."
                )
    scheduler_state = lister.get_state_from_scheduler()
    assert scheduler_state is not None
    assert scheduler_state.last_seen_doc == -1
    assert scheduler_state.last_seen_pom == -1


def test_maven_incremental_listing(
    swh_scheduler,
    requests_mock,
    mocker,
    maven_index,
    maven_index_incr,
    maven_pom_1,
    maven_pom_2,
    maven_pom_3,
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
    requests_mock.get(INDEX_URL, text=maven_index)
    requests_mock.get(URL_POM_1, text=maven_pom_1)
    requests_mock.get(URL_POM_2, text=maven_pom_2)

    # Then run the lister.
    stats = lister.run()

    # Start test checks.
    assert lister.incremental
    assert lister.updated
    assert stats.pages == 4
    assert stats.origins == 4

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
    assert scheduler_state.last_seen_doc == 3
    assert scheduler_state.last_seen_pom == 3

    # Set up test.
    requests_mock.get(INDEX_URL, text=maven_index_incr)
    requests_mock.get(URL_POM_3, text=maven_pom_3)

    # Then run the lister.
    stats = lister.run()

    # Start test checks.
    assert lister.incremental
    assert lister.updated
    assert stats.pages == 1
    assert stats.origins == 1

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    origin_urls = [origin.url for origin in scheduler_origins]
    assert sorted(origin_urls) == sorted(LIST_SRC + LIST_GIT + LIST_GIT_INCR)

    for origin in scheduler_origins:
        if origin.visit_type == "maven":
            for src in LIST_SRC_DATA:
                if src.get("url") == origin.url:
                    artifact = origin.extra_loader_arguments["artifacts"][0]
                    assert src.get("time") == artifact["time"]
                    assert src.get("gid") == artifact["gid"]
                    assert src.get("aid") == artifact["aid"]
                    assert src.get("version") == artifact["version"]
                    break
            else:
                raise AssertionError

    scheduler_state = lister.get_state_from_scheduler()
    assert scheduler_state is not None
    assert scheduler_state.last_seen_doc == 4
    assert scheduler_state.last_seen_pom == 4


@pytest.mark.parametrize("http_code", [400, 404, 500, 502])
def test_maven_list_http_error(
    swh_scheduler, requests_mock, mocker, maven_index, http_code
):
    """Test handling of some common HTTP errors:
    - 400: Bad request.
    - 404: Resource no found.
    - 500: Internal server error.
    - 502: Bad gateway ou proxy Error.
    """

    lister = MavenLister(scheduler=swh_scheduler, url=MVN_URL, index_url=INDEX_URL)

    # Test failure of index retrieval.

    requests_mock.get(INDEX_URL, status_code=http_code)

    with pytest.raises(requests.HTTPError):
        lister.run()

    # Test failure of artefacts retrieval.

    requests_mock.get(INDEX_URL, text=maven_index)
    requests_mock.get(URL_POM_1, status_code=http_code)

    with pytest.raises(requests.HTTPError):
        lister.run()

    # If the maven_index step succeeded but not the get_pom step,
    # then we get only the 2 maven-jar origins (and not the 2 additional
    # src origins).
    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    assert len(scheduler_origins) == 2
