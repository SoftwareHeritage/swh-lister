# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from collections import defaultdict
from itertools import chain
import json
from pathlib import Path

import pytest

from swh.lister.cpan.lister import CpanLister, get_module_version


@pytest.fixture
def release_search_response(datadir):
    return json.loads(
        Path(datadir, "https_fastapi.metacpan.org", "v1_release__search").read_bytes()
    )


def release_scroll_response(datadir, page):
    return json.loads(
        Path(
            datadir, "https_fastapi.metacpan.org", f"v1__search_scroll_page{page}"
        ).read_bytes()
    )


@pytest.fixture
def release_scroll_first_response(datadir):
    return release_scroll_response(datadir, page=1)


@pytest.fixture
def release_scroll_second_response(datadir):
    return release_scroll_response(datadir, page=2)


@pytest.fixture
def release_scroll_third_response(datadir):
    return release_scroll_response(datadir, page=3)


@pytest.fixture
def release_scroll_fourth_response(datadir):
    return release_scroll_response(datadir, page=4)


@pytest.fixture(autouse=True)
def mock_network_requests(
    requests_mock,
    release_search_response,
    release_scroll_first_response,
    release_scroll_second_response,
    release_scroll_third_response,
    release_scroll_fourth_response,
):
    requests_mock.get(
        "https://fastapi.metacpan.org/v1/release/_search",
        json=release_search_response,
    )
    requests_mock.get(
        "https://fastapi.metacpan.org/v1/_search/scroll",
        [
            {
                "json": release_scroll_first_response,
            },
            {
                "json": release_scroll_second_response,
            },
            {
                "json": release_scroll_third_response,
            },
            {
                "json": release_scroll_fourth_response,
            },
            {"json": {"hits": {"hits": []}, "_scroll_id": ""}},
        ],
    )


@pytest.mark.parametrize(
    "module_name,module_version,release_name,expected_version",
    [
        ("Validator-Custom", "0.1207", "Validator-Custom-0.1207", "0.1207"),
        ("UDPServersAndClients", 0, "UDPServersAndClients", "0"),
        ("Compiler", 0, "Compiler-a1", "a1"),
        ("Call-Context", 0.01, "Call-Context-0.01", "0.01"),
    ],
)
def test_get_module_version(
    module_name, module_version, release_name, expected_version
):
    assert (
        get_module_version(module_name, module_version, release_name)
        == expected_version
    )


def test_cpan_lister(
    swh_scheduler,
    release_search_response,
    release_scroll_first_response,
    release_scroll_second_response,
    release_scroll_third_response,
    release_scroll_fourth_response,
):
    lister = CpanLister(scheduler=swh_scheduler)
    res = lister.run()

    expected_origins = set()
    expected_artifacts = defaultdict(list)
    expected_module_metadata = defaultdict(list)
    for release in chain(
        release_search_response["hits"]["hits"],
        release_scroll_first_response["hits"]["hits"],
        release_scroll_second_response["hits"]["hits"],
        release_scroll_third_response["hits"]["hits"],
        release_scroll_fourth_response["hits"]["hits"],
    ):
        distribution = release["_source"]["distribution"]
        release_name = release["_source"]["name"]
        checksum_sha256 = release["_source"]["checksum_sha256"]
        download_url = release["_source"]["download_url"]
        version = release["_source"]["version"]
        size = release["_source"]["stat"]["size"]
        author = release["_source"]["author"]
        author_fullname = release["_source"]["metadata"]["author"][0]
        date = release["_source"]["date"]
        origin_url = f"https://metacpan.org/dist/{distribution}"

        version = get_module_version(distribution, version, release_name)

        expected_origins.add(origin_url)
        expected_artifacts[origin_url].append(
            {
                "url": download_url,
                "filename": download_url.split("/")[-1],
                "version": version,
                "length": size,
                "checksums": {"sha256": checksum_sha256},
            }
        )
        expected_module_metadata[origin_url].append(
            {
                "name": distribution,
                "version": version,
                "cpan_author": author,
                "author": author_fullname if author_fullname != "unknown" else author,
                "date": date,
                "release_name": release_name,
            }
        )

    assert res.pages == 1
    assert res.origins == len(expected_origins)

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    assert len(scheduler_origins) == len(expected_origins)

    for origin in scheduler_origins:
        assert origin.visit_type == "cpan"
        assert origin.url in expected_origins
        assert origin.extra_loader_arguments == {
            "api_base_url": "https://fastapi.metacpan.org/v1",
            "artifacts": expected_artifacts[origin.url],
            "module_metadata": expected_module_metadata[origin.url],
        }
