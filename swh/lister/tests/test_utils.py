# Copyright (C) 2018-2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import unittest

from testing.postgresql import Postgresql

from swh.lister import utils


class UtilsTest(unittest.TestCase):
    def test_split_range(self):
        actual_ranges = list(utils.split_range(14, 5))
        self.assertEqual(actual_ranges, [(0, 5), (5, 10), (10, 14)])

        actual_ranges = list(utils.split_range(19, 10))
        self.assertEqual(actual_ranges, [(0, 10), (10, 19)])

    def test_split_range_errors(self):
        with self.assertRaises(TypeError):
            list(utils.split_range(None, 1))

        with self.assertRaises(TypeError):
            list(utils.split_range(100, None))


def init_db():
    """Factorize the db_url instantiation

    Returns:
        db object to ease db manipulation

    """
    initdb_args = Postgresql.DEFAULT_SETTINGS["initdb_args"]
    initdb_args = " ".join([initdb_args, "-E UTF-8"])
    return Postgresql(initdb_args=initdb_args)
