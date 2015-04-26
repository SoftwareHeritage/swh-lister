
from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.ext.declarative import declarative_base


SQLBase = declarative_base()


class Repository(SQLBase):

    """a GitHub repository"""

    __tablename__ = 'repos'

    id = Column(Integer, primary_key=True)

    name = Column(String, index=True)
    full_name = Column(String, index=True)
    html_url = Column(String)
    description = Column(String)
    fork = Column(Boolean, index=True)

    last_seen = Column(DateTime, nullable=False)

    def __init__(self, id, name=None, full_name=None, html_url=None,
                 description=None, fork=None):
        self.id = id
        self.last_seen = datetime.now()
        if name is not None:
            self.name = name
        if full_name is not None:
            self.full_name = full_name
        if html_url is not None:
            self.html_url = html_url
        if description is not None:
            self.description = description
        if fork is not None:
            self.fork = fork
