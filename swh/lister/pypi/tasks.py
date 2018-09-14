# Copyright (C) 2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from ..core.tasks import ListerTaskBase
from .lister import PyPILister


class PyPIListerTask(ListerTaskBase):
    """Full PyPI lister (list all available origins from the api).

    """
    task_queue = 'swh_lister_pypi_refresh'

    def new_lister(self):
        return PyPILister()

    def run_task(self):
        lister = self.new_lister()
        lister.run()
