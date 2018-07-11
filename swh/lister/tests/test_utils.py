# Copyright (C) 2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import unittest

from nose.tools import istest

from swh.lister import utils


class UtilsTest(unittest.TestCase):

    @istest
    def get(self):
        data = {
            'X-Next-Page': None,
            'x-next-page': 1,
        }
        actual_value = utils.get(data, ['X-Next-Page', 'x-next-page'])

        self.assertEqual(actual_value, 1)

        data = {
            'X-Next-Page': 10,
            'x-next-page': 1,
        }
        actual_value = utils.get(data, ['X-Next-Page', 'x-next-page'])

        self.assertEqual(actual_value, 10)

        data = {
            'x-next-page': 100,
        }
        actual_value = utils.get(data, ['X-Next-Page', 'x-next-page'])

        self.assertEqual(actual_value, 100)

    @istest
    def get_empty(self):
        self.assertIsNone(utils.get({}, []))
        self.assertIsNone(utils.get({'a': 1}, ['b']))
        self.assertIsNone(utils.get({'b': 2}, []))
        self.assertIsNone(utils.get({'b': 2}, []))

    @istest
    def get_errors(self):
        with self.assertRaises(TypeError):
            self.assertIsNone(utils.get({}, None))
        with self.assertRaises(AttributeError):
            self.assertIsNone(utils.get(None, ['a']))
