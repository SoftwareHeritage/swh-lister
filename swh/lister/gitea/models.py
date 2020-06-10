# Copyright (C) 2020 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from sqlalchemy import Column, Integer, String

from ..core.models import ModelBase


class GiteaModel(ModelBase):
    """a Gitea repository from a gitea instance

    """

    __tablename__ = "gitea_repo"

    uid = Column(Integer, primary_key=True)
    instance = Column(String, index=True)
