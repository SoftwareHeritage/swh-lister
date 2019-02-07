# Copyright (C) 2015-2017 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import abc
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta

from .abstractattribute import AbstractAttribute

SQLBase = declarative_base()


class ABCSQLMeta(abc.ABCMeta, DeclarativeMeta):
    pass


class ModelBase(SQLBase, metaclass=ABCSQLMeta):
    """a common repository"""
    __abstract__ = True
    __tablename__ = AbstractAttribute

    uid = AbstractAttribute('Column(<uid_type>, primary_key=True)')

    name = Column(String, index=True)
    full_name = Column(String, index=True)
    html_url = Column(String)
    origin_url = Column(String)
    origin_type = Column(String)
    description = Column(String)

    last_seen = Column(DateTime, nullable=False)

    task_id = Column(Integer)
    origin_id = Column(Integer)

    def __init__(self, **kw):
        kw['last_seen'] = datetime.now()
        super().__init__(**kw)


class IndexingModelBase(ModelBase, metaclass=ABCSQLMeta):
    __abstract__ = True
    __tablename__ = AbstractAttribute

    # The value used for sorting, segmenting, or api query paging,
    # because uids aren't always sequential.
    indexable = AbstractAttribute('Column(<indexable_type>, index=True)')
