# Copyright (C) 2017-2020 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from sqlalchemy import Column, Date, String

from swh.lister.core.models import ModelBase


class LaunchpadModel(ModelBase):
    """a Launchpad repository"""

    __tablename__ = "launchpad_repo"

    uid = Column(String, primary_key=True)
    date_last_modified = Column(Date, index=True)
