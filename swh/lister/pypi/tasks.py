# Copyright (C) 2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.scheduler.task import SWHTask
from swh.scheduler.celery_backend.config import app

from .lister import PyPILister


@app.task(name='swh.lister.pypi.tasks.PyPIListerTask',
          base=SWHTask, bind=True)
def pypi_lister(self, **lister_args):
    self.log.debug('%s(), lister_args=%s' % (
        self.name, lister_args))
    PyPILister(**lister_args).run()
    self.log.debug('%s OK' % (self.name))


