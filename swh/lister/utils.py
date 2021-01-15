# Copyright (C) 2018-2021 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Iterator, Tuple

from requests.exceptions import HTTPError
from requests.status_codes import codes
from tenacity import retry as tenacity_retry
from tenacity.stop import stop_after_attempt
from tenacity.wait import wait_exponential


def split_range(total_pages: int, nb_pages: int) -> Iterator[Tuple[int, int]]:
    """Split `total_pages` into mostly `nb_pages` ranges. In some cases, the last range can
    have one more element.

    >>> list(split_range(19, 10))
    [(0, 9), (10, 19)]

    >>> list(split_range(20, 3))
    [(0, 2), (3, 5), (6, 8), (9, 11), (12, 14), (15, 17), (18, 20)]

    >>> list(split_range(21, 3))
    [(0, 2), (3, 5), (6, 8), (9, 11), (12, 14), (15, 17), (18, 21)]

    """
    prev_index = None
    for index in range(0, total_pages, nb_pages):
        if index is not None and prev_index is not None:
            yield prev_index, index - 1
        prev_index = index

    if index != total_pages:
        yield index, total_pages


def is_throttling_exception(e: Exception) -> bool:
    """
    Checks if an exception is a requests.exception.HTTPError for
    a response with status code 429 (too many requests).
    """
    return (
        isinstance(e, HTTPError) and e.response.status_code == codes.too_many_requests
    )


def retry_attempt(retry_state):
    """
    Utility function to get last retry attempt info based on the
    tenacity version (as debian buster packages version 4.12).
    """
    try:
        attempt = retry_state.outcome
    except AttributeError:
        # tenacity < 5.0
        attempt = retry_state
    return attempt


def retry_if_throttling(retry_state) -> bool:
    """
    Custom tenacity retry predicate for handling HTTP responses with
    status code 429 (too many requests).
    """
    attempt = retry_attempt(retry_state)
    if attempt.failed:
        exception = attempt.exception()
        return is_throttling_exception(exception)
    return False


WAIT_EXP_BASE = 10
MAX_NUMBER_ATTEMPTS = 5


def throttling_retry(
    retry=retry_if_throttling,
    wait=wait_exponential(exp_base=WAIT_EXP_BASE),
    stop=stop_after_attempt(max_attempt_number=MAX_NUMBER_ATTEMPTS),
    **retry_args,
):
    """
    Decorator based on `tenacity` for retrying a function possibly raising
    requests.exception.HTTPError for status code 429 (too many requests).

    It provides a default configuration that should work properly in most
    cases but all `tenacity.retry` parameters can also be overridden in client
    code.

    When the mmaximum of attempts is reached, the HTTPError exception will then
    be reraised.

    Args:
        retry: function defining request retry condition (default to 429 status code)
            https://tenacity.readthedocs.io/en/latest/#whether-to-retry

        wait: function defining wait strategy before retrying (default to exponential
            backoff) https://tenacity.readthedocs.io/en/latest/#waiting-before-retrying

        stop: function defining when to stop retrying (default after 5 attempts)
            https://tenacity.readthedocs.io/en/latest/#stopping

    """
    return tenacity_retry(retry=retry, wait=wait, stop=stop, reraise=True, **retry_args)
