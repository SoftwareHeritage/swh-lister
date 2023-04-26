# Copyright (C) 2018-2023 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Iterator, Optional, Tuple
import urllib.parse


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


def is_valid_origin_url(url: Optional[str]) -> bool:
    """Returns whether the given string is a valid origin URL.
    This excludes Git SSH URLs and pseudo-URLs (eg. ``ssh://git@example.org:foo``
    and ``git@example.org:foo``), as they are not supported by the Git loader
    and usually require authentication.

    All HTTP URLs are allowed:

    >>> is_valid_origin_url("http://example.org/repo.git")
    True
    >>> is_valid_origin_url("http://example.org/repo")
    True
    >>> is_valid_origin_url("https://example.org/repo")
    True
    >>> is_valid_origin_url("https://foo:bar@example.org/repo")
    True

    Scheme-less URLs are rejected;

    >>> is_valid_origin_url("example.org/repo")
    False
    >>> is_valid_origin_url("example.org:repo")
    False

    Git SSH URLs and pseudo-URLs are rejected:

    >>> is_valid_origin_url("git@example.org:repo")
    False
    >>> is_valid_origin_url("ssh://git@example.org:repo")
    False
    """
    if not url:
        # Empty or None
        return False

    parsed = urllib.parse.urlparse(url)
    if not parsed.netloc:
        # Is parsed as a relative URL
        return False

    if parsed.scheme == "ssh":
        # Git SSH URL
        return False

    return True
