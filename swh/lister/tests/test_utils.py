# Copyright (C) 2018-2021 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest
import requests
from requests.status_codes import codes
from tenacity.wait import wait_fixed

from swh.lister.utils import (
    MAX_NUMBER_ATTEMPTS,
    WAIT_EXP_BASE,
    split_range,
    throttling_retry,
)


@pytest.mark.parametrize(
    "total_pages,nb_pages,expected_ranges",
    [
        (14, 5, [(0, 4), (5, 9), (10, 14)]),
        (19, 10, [(0, 9), (10, 19)]),
        (20, 3, [(0, 2), (3, 5), (6, 8), (9, 11), (12, 14), (15, 17), (18, 20)]),
        (21, 3, [(0, 2), (3, 5), (6, 8), (9, 11), (12, 14), (15, 17), (18, 21),],),
    ],
)
def test_split_range(total_pages, nb_pages, expected_ranges):
    actual_ranges = list(split_range(total_pages, nb_pages))
    assert actual_ranges == expected_ranges


@pytest.mark.parametrize("total_pages,nb_pages", [(None, 1), (100, None)])
def test_split_range_errors(total_pages, nb_pages):
    for total_pages, nb_pages in [(None, 1), (100, None)]:
        with pytest.raises(TypeError):
            next(split_range(total_pages, nb_pages))


TEST_URL = "https://example.og/api/repositories"


@throttling_retry()
def make_request():
    response = requests.get(TEST_URL)
    response.raise_for_status()
    return response


def assert_sleep_calls(mocker, mock_sleep, sleep_params):
    mock_sleep.assert_has_calls([mocker.call(param) for param in sleep_params])


def test_throttling_retry(requests_mock, mocker):
    data = {"result": {}}
    requests_mock.get(
        TEST_URL,
        [
            {"status_code": codes.too_many_requests},
            {"status_code": codes.too_many_requests},
            {"status_code": codes.ok, "json": data},
        ],
    )

    mock_sleep = mocker.patch.object(make_request.retry, "sleep")

    response = make_request()

    assert_sleep_calls(mocker, mock_sleep, [1, WAIT_EXP_BASE])

    assert response.json() == data


def test_throttling_retry_max_attemps(requests_mock, mocker):
    requests_mock.get(
        TEST_URL, [{"status_code": codes.too_many_requests}] * (MAX_NUMBER_ATTEMPTS),
    )

    mock_sleep = mocker.patch.object(make_request.retry, "sleep")

    with pytest.raises(requests.exceptions.HTTPError) as e:
        make_request()

    assert e.value.response.status_code == codes.too_many_requests

    assert_sleep_calls(
        mocker,
        mock_sleep,
        [float(WAIT_EXP_BASE ** i) for i in range(MAX_NUMBER_ATTEMPTS - 1)],
    )


@throttling_retry(wait=wait_fixed(WAIT_EXP_BASE))
def make_request_wait_fixed():
    response = requests.get(TEST_URL)
    response.raise_for_status()
    return response


def test_throttling_retry_wait_fixed(requests_mock, mocker):
    requests_mock.get(
        TEST_URL,
        [
            {"status_code": codes.too_many_requests},
            {"status_code": codes.too_many_requests},
            {"status_code": codes.ok},
        ],
    )

    mock_sleep = mocker.patch.object(make_request_wait_fixed.retry, "sleep")

    make_request_wait_fixed()

    assert_sleep_calls(mocker, mock_sleep, [WAIT_EXP_BASE] * 2)
