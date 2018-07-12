# Copyright (C) 2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


def get(d, keys):
    """Given a dict, lookup in order for keys with values not None.

    """
    for key in keys:
        v = d.get(key)
        if v is not None:
            return v
    return None


def split_range(total_pages, nb_pages):
    prev_index = None
    for index in range(0, total_pages, nb_pages):
        if index is not None and prev_index is not None:
            yield prev_index, index
        prev_index = index

    if index != total_pages:
        yield index, total_pages
