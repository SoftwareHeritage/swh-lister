# Copyright (C) 2017-2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.lister.core.tasks import ListerTaskBase

from .lister import DebianLister


class DebianListerTask(ListerTaskBase):
    task_queue = 'swh_lister_debian'

    def new_lister(self):
        return DebianLister()

    def run_task(self, distribution):
        lister = self.new_lister()
        return lister.run(distribution)
