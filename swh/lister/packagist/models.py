# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from sqlalchemy import Column, String

from ..core.models import ModelBase


class PackagistModel(ModelBase):
    """a Packagist repository representation

    """

    __tablename__ = "packagist_repo"

    uid = Column(String, primary_key=True)
