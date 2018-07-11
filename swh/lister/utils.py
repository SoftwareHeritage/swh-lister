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
