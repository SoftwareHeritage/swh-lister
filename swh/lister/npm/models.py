# Copyright (C) 2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from sqlalchemy import Column, String

from swh.lister.core.models import IndexingModelBase


class NpmModel(IndexingModelBase):
    """a npm repository representation

    """
    __tablename__ = 'npm_repo'

    uid = Column(String, primary_key=True)
    indexable = Column(String, index=True)
