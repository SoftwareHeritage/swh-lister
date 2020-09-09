# Copyright (C) 2018-2020 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest

from testing.postgresql import Postgresql

from swh.lister import utils


@pytest.mark.parametrize(
    "total_pages,nb_pages,expected_ranges",
    [(14, 5, [(0, 5), (5, 10), (10, 14)]), (19, 10, [(0, 10), (10, 19)])],
)
def test_split_range(total_pages, nb_pages, expected_ranges):
    actual_ranges = list(utils.split_range(total_pages, nb_pages))
    assert actual_ranges == expected_ranges


@pytest.mark.parametrize("total_pages,nb_pages", [(None, 1), (100, None)])
def test_split_range_errors(total_pages, nb_pages):
    for total_pages, nb_pages in [(None, 1), (100, None)]:
        with pytest.raises(TypeError):
            next(utils.split_range(total_pages, nb_pages))


def init_db():
    """Factorize the db_url instantiation

    Returns:
        db object to ease db manipulation

    """
    initdb_args = Postgresql.DEFAULT_SETTINGS["initdb_args"]
    initdb_args = " ".join([initdb_args, "-E UTF-8"])
    return Postgresql(initdb_args=initdb_args)
