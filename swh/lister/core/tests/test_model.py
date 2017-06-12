# Copyright (C) 2017 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import unittest

from nose.tools import istest
from sqlalchemy import Column, Integer

from swh.lister.core.models import ModelBase


class BadSubclass1(ModelBase):
    __abstract__ = True
    pass


class BadSubclass2(ModelBase):
    __abstract__ = True
    __tablename__ = 'foo'


class BadSubclass3(BadSubclass2):
    __abstract__ = True
    pass


class GoodSubclass(BadSubclass2):
    uid = Column(Integer, primary_key=True)
    indexable = Column(Integer, index=True)


class TestModel(unittest.TestCase):
    @istest
    def test_model_instancing(self):
        with self.assertRaises(TypeError):
            ModelBase()

        with self.assertRaises(TypeError):
            BadSubclass1()

        with self.assertRaises(TypeError):
            BadSubclass2()

        with self.assertRaises(TypeError):
            BadSubclass3()

        self.assertIsInstance(GoodSubclass(), GoodSubclass)
        gsc = GoodSubclass(uid='uid', indexable='indexable')

        self.assertEqual(gsc.__tablename__, 'foo')
        self.assertEqual(gsc.uid, 'uid')
        self.assertEqual(gsc.indexable, 'indexable')
