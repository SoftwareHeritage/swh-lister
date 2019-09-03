# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.scheduler.celery_backend.config import app

from .lister import CGitLister


@app.task(name=__name__ + '.CGitListerTask')
def list_cgit(**lister_args):
    '''Lister task for CGit instances'''
    CGitLister(**lister_args).run()


@app.task(name=__name__ + '.ping')
def _ping():
    return 'OK'
