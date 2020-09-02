# Copyright (C) 2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from sqlalchemy import Column, String

from ..core.models import ModelBase


class PyPIModel(ModelBase):
    """a PyPI repository representation

    """

    __tablename__ = "pypi_repo"

    uid = Column(String, primary_key=True)
