# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from sqlalchemy import Column, String

from swh.lister.core.models import ModelBase


class CRANModel(ModelBase):
    """a CRAN repository representation

    """

    __tablename__ = "cran_repo"

    uid = Column(String, primary_key=True)
    version = Column(String)
