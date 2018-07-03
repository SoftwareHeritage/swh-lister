# Copyright (C) 2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from sqlalchemy import Column, Integer, String

from ..core.models import ModelBase


class GitLabModel(ModelBase):
    """a Gitlab repository from a gitlab instance

    """
    __tablename__ = 'gitlab_repo'

    id = Column(Integer, primary_key=True)
    uid = Column(Integer, index=True)
    instance = Column(String, index=True)
    indexable = Column(Integer, index=True)

    def __init__(self, uid=None, indexable=None, name=None,
                 full_name=None, html_url=None, origin_url=None,
                 origin_type=None, description=None, task_id=None,
                 origin_id=None, instance=None):
        super().__init__(uid=uid, indexable=indexable, name=name,
                         full_name=full_name, html_url=html_url,
                         origin_url=origin_url, origin_type=origin_type,
                         description=description, task_id=task_id,
                         origin_id=origin_id)
        self.instance = instance
