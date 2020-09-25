# Copyright (C) 2017-2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from sqlalchemy import Boolean, Column, Integer

from swh.lister.core.models import IndexingModelBase


class GitHubModel(IndexingModelBase):
    """a GitHub repository"""

    __tablename__ = "github_repo"

    uid = Column(Integer, primary_key=True)
    indexable = Column(Integer, index=True)
    fork = Column(Boolean, default=False)
