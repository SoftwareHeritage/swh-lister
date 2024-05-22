# Copyright (C) 2024  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from operator import attrgetter, itemgetter
import re
import string

import pytest
import requests

from swh.lister.pattern import ListerStats
from swh.lister.save_bulk.lister import (
    CONNECTION_ERROR,
    HOSTNAME_ERROR,
    HTTP_ERROR,
    VISIT_TYPE_ERROR,
    RejectedOrigin,
    SaveBulkLister,
    SubmittedOrigin,
    is_valid_cvs_url,
)

URL = "https://example.org/origins/list/"
INSTANCE = "some-instance"

PER_PAGE = 2

SUBMITTED_ORIGINS = [
    SubmittedOrigin(origin_url=origin_url, visit_type=visit_type)
    for origin_url, visit_type in [
        ("https://example.org/download/tarball.tar.gz", "tarball-directory"),
        ("https://git.example.org/user/project.git", "git"),
        ("https://svn.example.org/project/trunk", "svn"),
        ("https://hg.example.org/projects/test", "hg"),
        ("https://bzr.example.org/projects/test", "bzr"),
        ("rsync://cvs.example.org/cvsroot/project/module", "cvs"),
    ]
]


@pytest.fixture(autouse=True)
def origins_list_requests_mock(requests_mock):
    nb_pages = len(SUBMITTED_ORIGINS) // PER_PAGE
    for i in range(nb_pages):
        requests_mock.get(
            f"{URL}?page={i+1}&per_page={PER_PAGE}",
            json=SUBMITTED_ORIGINS[i * PER_PAGE : (i + 1) * PER_PAGE],
        )
    requests_mock.get(
        f"{URL}?page={nb_pages+1}&per_page={PER_PAGE}",
        json=[],
    )


@pytest.mark.parametrize(
    "valid_cvs_url",
    [
        "rsync://cvs.example.org/project/module",
        "pserver://anonymous@cvs.example.org/project/module",
    ],
)
def test_is_valid_cvs_url_success(valid_cvs_url):
    assert is_valid_cvs_url(valid_cvs_url) == (True, None)


@pytest.mark.parametrize(
    "invalid_cvs_url",
    [
        "rsync://cvs.example.org/project",
        "pserver://anonymous@cvs.example.org/project",
        "pserver://cvs.example.org/project/module",
        "http://cvs.example.org/project/module",
    ],
)
def test_is_valid_cvs_url_failure(invalid_cvs_url):
    err_msg_prefix = "The origin URL for the CVS repository is malformed"
    ret, err_msg = is_valid_cvs_url(invalid_cvs_url)
    assert not ret and err_msg.startswith(err_msg_prefix)


def test_bulk_lister_valid_origins(swh_scheduler, requests_mock, mocker):
    requests_mock.head(re.compile(".*"), status_code=200)
    mocker.patch("swh.lister.save_bulk.lister.socket.getaddrinfo").return_value = [
        ("125.25.14.15", 0)
    ]
    for origin in SUBMITTED_ORIGINS:
        visit_type = origin["visit_type"].split("-", 1)[0]
        mocker.patch(
            f"swh.lister.save_bulk.lister.is_valid_{visit_type}_url"
        ).return_value = (True, None)

    lister_bulk = SaveBulkLister(
        url=URL,
        instance=INSTANCE,
        scheduler=swh_scheduler,
        per_page=PER_PAGE,
    )
    stats = lister_bulk.run()

    expected_nb_origins = len(SUBMITTED_ORIGINS)
    assert stats == ListerStats(
        pages=expected_nb_origins // PER_PAGE, origins=expected_nb_origins
    )

    state = lister_bulk.get_state_from_scheduler()

    assert sorted(
        [
            SubmittedOrigin(origin_url=origin.url, visit_type=origin.visit_type)
            for origin in swh_scheduler.get_listed_origins(
                lister_bulk.lister_obj.id
            ).results
        ],
        key=itemgetter("visit_type"),
    ) == sorted(SUBMITTED_ORIGINS, key=itemgetter("visit_type"))
    assert state.rejected_origins == []


def test_bulk_lister_not_found_origins(swh_scheduler, requests_mock, mocker):
    requests_mock.head(re.compile(".*"), status_code=404)
    mocker.patch("swh.lister.save_bulk.lister.socket.getaddrinfo").side_effect = (
        OSError("Hostname not found")
    )

    lister_bulk = SaveBulkLister(
        url=URL,
        instance=INSTANCE,
        scheduler=swh_scheduler,
        per_page=PER_PAGE,
    )
    stats = lister_bulk.run()

    assert stats == ListerStats(pages=len(SUBMITTED_ORIGINS) // PER_PAGE, origins=0)

    state = lister_bulk.get_state_from_scheduler()

    assert list(sorted(state.rejected_origins, key=attrgetter("origin_url"))) == list(
        sorted(
            [
                RejectedOrigin(
                    origin_url=o["origin_url"],
                    visit_type=o["visit_type"],
                    reason=(
                        HTTP_ERROR + ": 404 - Not Found"
                        if o["origin_url"].startswith("http")
                        else HOSTNAME_ERROR
                    ),
                    exception=(
                        f"404 Client Error: None for url: {o['origin_url']}"
                        if o["origin_url"].startswith("http")
                        else "Hostname not found"
                    ),
                )
                for o in SUBMITTED_ORIGINS
            ],
            key=attrgetter("origin_url"),
        )
    )


def test_bulk_lister_connection_errors(swh_scheduler, requests_mock, mocker):
    requests_mock.head(
        re.compile(".*"),
        exc=requests.exceptions.ConnectionError("connection error"),
    )
    mocker.patch("swh.lister.save_bulk.lister.socket.getaddrinfo").side_effect = (
        OSError("Hostname not found")
    )

    lister_bulk = SaveBulkLister(
        url=URL,
        instance=INSTANCE,
        scheduler=swh_scheduler,
        per_page=PER_PAGE,
    )
    stats = lister_bulk.run()

    assert stats == ListerStats(pages=len(SUBMITTED_ORIGINS) // PER_PAGE, origins=0)

    state = lister_bulk.get_state_from_scheduler()

    assert list(sorted(state.rejected_origins, key=attrgetter("origin_url"))) == list(
        sorted(
            [
                RejectedOrigin(
                    origin_url=o["origin_url"],
                    visit_type=o["visit_type"],
                    reason=(
                        CONNECTION_ERROR
                        if o["origin_url"].startswith("http")
                        else HOSTNAME_ERROR
                    ),
                    exception=(
                        "connection error"
                        if o["origin_url"].startswith("http")
                        else "Hostname not found"
                    ),
                )
                for o in SUBMITTED_ORIGINS
            ],
            key=attrgetter("origin_url"),
        )
    )


def test_bulk_lister_invalid_origins(swh_scheduler, requests_mock, mocker):
    requests_mock.head(re.compile(".*"), status_code=200)
    mocker.patch("swh.lister.save_bulk.lister.socket.getaddrinfo").return_value = [
        ("125.25.14.15", 0)
    ]

    exc_msg_template = string.Template(
        "error: the origin url does not target a public $visit_type repository."
    )
    for origin in SUBMITTED_ORIGINS:
        visit_type = origin["visit_type"].split("-", 1)[0]
        visit_type_check = mocker.patch(
            f"swh.lister.save_bulk.lister.is_valid_{visit_type}_url"
        )
        if visit_type == "tarball":
            visit_type_check.return_value = (True, None)
        else:
            visit_type_check.return_value = (
                False,
                exc_msg_template.substitute(visit_type=visit_type),
            )

    lister_bulk = SaveBulkLister(
        url=URL,
        instance=INSTANCE,
        scheduler=swh_scheduler,
        per_page=PER_PAGE,
    )
    stats = lister_bulk.run()

    assert stats == ListerStats(pages=len(SUBMITTED_ORIGINS) // PER_PAGE, origins=1)

    assert [
        SubmittedOrigin(origin_url=origin.url, visit_type=origin.visit_type)
        for origin in swh_scheduler.get_listed_origins(
            lister_bulk.lister_obj.id
        ).results
    ] == [SUBMITTED_ORIGINS[0]]

    state = lister_bulk.get_state_from_scheduler()

    assert list(sorted(state.rejected_origins, key=attrgetter("origin_url"))) == list(
        sorted(
            [
                RejectedOrigin(
                    origin_url=o["origin_url"],
                    visit_type=o["visit_type"],
                    reason=VISIT_TYPE_ERROR[o["visit_type"]],
                    exception=exc_msg_template.substitute(visit_type=o["visit_type"]),
                )
                for o in SUBMITTED_ORIGINS
                if o["visit_type"] != "tarball-directory"
            ],
            key=attrgetter("origin_url"),
        )
    )
