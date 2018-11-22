# Copyright (C) 2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.lister.core.tasks import ListerTaskBase
from swh.lister.npm.lister import NpmLister


class NpmListerTask(ListerTaskBase):
    """Full npm lister (list all available packages from the npm registry).

    """
    task_queue = 'swh_lister_npm_refresh'

    def new_lister(self):
        return NpmLister()

    def run_task(self):
        lister = self.new_lister()
        lister.run()
