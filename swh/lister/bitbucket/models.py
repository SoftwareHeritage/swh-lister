# Copyright (C) 2017-2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from sqlalchemy import Column, String

from swh.lister.core.models import IndexingModelBase


class BitBucketModel(IndexingModelBase):
    """a BitBucket repository"""
    __tablename__ = 'bitbucket_repos'

    uid = Column(String, primary_key=True)
    indexable = Column(String, index=True)
