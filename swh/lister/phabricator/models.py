# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from sqlalchemy import Column, Integer, String

from swh.lister.core.models import IndexingModelBase


class PhabricatorModel(IndexingModelBase):
    """a Phabricator repository"""

    __tablename__ = "phabricator_repo"

    uid = Column(String, primary_key=True)
    indexable = Column(Integer, index=True)
    instance = Column(String, index=True)
