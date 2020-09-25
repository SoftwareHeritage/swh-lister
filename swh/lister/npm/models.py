# Copyright (C) 2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from sqlalchemy import BigInteger, Column, DateTime, Integer, Sequence, String

from swh.lister.core.models import ABCSQLMeta, IndexingModelBase, SQLBase


class NpmVisitModel(SQLBase, metaclass=ABCSQLMeta):
    """Table to store the npm registry state at the time of a
    content listing by Software Heritage
    """

    __tablename__ = "npm_visit"

    uid = Column(Integer, Sequence("npm_visit_id_seq"), primary_key=True)
    visit_date = Column(DateTime, nullable=False)
    doc_count = Column(BigInteger)
    doc_del_count = Column(BigInteger)
    update_seq = Column(BigInteger)
    purge_seq = Column(BigInteger)
    disk_size = Column(BigInteger)
    data_size = Column(BigInteger)
    committed_update_seq = Column(BigInteger)
    compacted_seq = Column(BigInteger)


class NpmModel(IndexingModelBase):
    """A npm package representation

    """

    __tablename__ = "npm_repo"

    uid = Column(String, primary_key=True)
    indexable = Column(String, index=True)
