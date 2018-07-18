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

    def __init__(self, uid=None, name=None, full_name=None,
                 html_url=None, origin_url=None, origin_type=None,
                 description=None, task_id=None, origin_id=None):
        self.uid = uid
        self.last_seen = datetime.now()

        if name is not None:
            self.name = name
        if full_name is not None:
            self.full_name = full_name
        if html_url is not None:
            self.html_url = html_url
        if origin_url is not None:
            self.origin_url = origin_url
        if origin_type is not None:
            self.origin_type = origin_type
        if description is not None:
            self.description = description

        if task_id is not None:
            self.task_id = task_id
        if origin_id is not None:
            self.origin_id = origin_id


class IndexingModelBase(ModelBase, metaclass=ABCSQLMeta):
    __abstract__ = True
    __tablename__ = AbstractAttribute

    # The value used for sorting, segmenting, or api query paging,
    # because uids aren't always sequential.
    indexable = AbstractAttribute('Column(<indexable_type>, index=True)')

    def __init__(self, uid=None, name=None, full_name=None,
                 html_url=None, origin_url=None, origin_type=None,
                 description=None, task_id=None, origin_id=None,
                 indexable=None):
        super().__init__(
            uid=uid, name=name, full_name=full_name, html_url=html_url,
            origin_url=origin_url, origin_type=origin_type,
            description=description, task_id=task_id, origin_id=origin_id)

        if indexable is not None:
            self.indexable = indexable
