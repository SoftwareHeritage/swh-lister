# Copyright (C) 2017-2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from sqlalchemy import Column, DateTime, String

from swh.lister.core.models import IndexingModelBase


class BitBucketModel(IndexingModelBase):
    """a BitBucket repository"""

    __tablename__ = "bitbucket_repo"

    uid = Column(String, primary_key=True)
    indexable = Column(DateTime(timezone=True), index=True)
