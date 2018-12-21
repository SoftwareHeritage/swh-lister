# Copyright (C) 2017-2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.scheduler.celery_backend.config import app
from swh.scheduler.task import SWHTask

from .lister import DebianLister


@app.task(name='swh.lister.debian.tasks.DebianListerTask',
          base=SWHTask, bind=True)
def debian_lister(self, distribution, **lister_args):
    self.log.debug('%s, lister_args=%s' % (
        self.name, lister_args))
    DebianLister(**lister_args).run(distribution)
    self.log.debug('%s OK' % (self.name))


@app.task(name='swh.lister.debian.tasks.ping',
          base=SWHTask, bind=True)
def ping(self):
    self.log.debug(self.name)
    return 'OK'
