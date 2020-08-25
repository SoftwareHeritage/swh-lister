# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from sqlalchemy import Column, DateTime, String

from ..core.models import ModelBase


class GNUModel(ModelBase):
    """a GNU repository representation

    """

    __tablename__ = "gnu_repo"

    uid = Column(String, primary_key=True)
    time_last_updated = Column(DateTime)
