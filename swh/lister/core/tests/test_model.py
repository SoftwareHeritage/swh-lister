# Copyright (C) 2017 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import unittest

from sqlalchemy import Column, Integer

from swh.lister.core.models import IndexingModelBase, ModelBase


class BadSubclass1(ModelBase):
    __abstract__ = True
    pass


class BadSubclass2(ModelBase):
    __abstract__ = True
    __tablename__ = "foo"


class BadSubclass3(BadSubclass2):
    __abstract__ = True
    pass


class GoodSubclass(BadSubclass2):
    uid = Column(Integer, primary_key=True)
    indexable = Column(Integer, index=True)


class IndexingBadSubclass(IndexingModelBase):
    __abstract__ = True
    pass


class IndexingBadSubclass2(IndexingModelBase):
    __abstract__ = True
    __tablename__ = "foo"


class IndexingBadSubclass3(IndexingBadSubclass2):
    __abstract__ = True
    pass


class IndexingGoodSubclass(IndexingModelBase):
    uid = Column(Integer, primary_key=True)
    indexable = Column(Integer, index=True)
    __tablename__ = "bar"


class TestModel(unittest.TestCase):
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
        gsc = GoodSubclass(uid="uid")

        self.assertEqual(gsc.__tablename__, "foo")
        self.assertEqual(gsc.uid, "uid")

    def test_indexing_model_instancing(self):
        with self.assertRaises(TypeError):
            IndexingModelBase()

        with self.assertRaises(TypeError):
            IndexingBadSubclass()

        with self.assertRaises(TypeError):
            IndexingBadSubclass2()

        with self.assertRaises(TypeError):
            IndexingBadSubclass3()

        self.assertIsInstance(IndexingGoodSubclass(), IndexingGoodSubclass)
        gsc = IndexingGoodSubclass(uid="uid", indexable="indexable")

        self.assertEqual(gsc.__tablename__, "bar")
        self.assertEqual(gsc.uid, "uid")
        self.assertEqual(gsc.indexable, "indexable")
