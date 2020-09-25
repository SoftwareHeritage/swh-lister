# Copyright (C) 2017 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import abc
from typing import Any
import unittest

from swh.lister.core.abstractattribute import AbstractAttribute


class BaseClass(abc.ABC):
    v1 = AbstractAttribute  # type: Any
    v2 = AbstractAttribute()  # type: Any
    v3 = AbstractAttribute("changed docstring")  # type: Any
    v4 = "qux"


class BadSubclass1(BaseClass):
    pass


class BadSubclass2(BaseClass):
    v1 = "foo"
    v2 = "bar"


class BadSubclass3(BaseClass):
    v2 = "bar"
    v3 = "baz"


class GoodSubclass(BaseClass):
    v1 = "foo"
    v2 = "bar"
    v3 = "baz"


class TestAbstractAttributes(unittest.TestCase):
    def test_aa(self):
        with self.assertRaises(TypeError):
            BaseClass()

        with self.assertRaises(TypeError):
            BadSubclass1()

        with self.assertRaises(TypeError):
            BadSubclass2()

        with self.assertRaises(TypeError):
            BadSubclass3()

        self.assertIsInstance(GoodSubclass(), GoodSubclass)
        gsc = GoodSubclass()

        self.assertEqual(gsc.v1, "foo")
        self.assertEqual(gsc.v2, "bar")
        self.assertEqual(gsc.v3, "baz")
        self.assertEqual(gsc.v4, "qux")

    def test_aa_docstrings(self):
        self.assertEqual(BaseClass.v1.__doc__, AbstractAttribute.__doc__)
        self.assertEqual(BaseClass.v2.__doc__, AbstractAttribute.__doc__)
        self.assertEqual(BaseClass.v3.__doc__, "AbstractAttribute: changed docstring")
