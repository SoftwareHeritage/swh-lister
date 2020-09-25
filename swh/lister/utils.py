# Copyright (C) 2018-2020 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Iterator, Tuple


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
