# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.scheduler.celery_backend.config import app

from .lister import GNULister


@app.task(name=__name__ + '.GNUListerTask')
def gnu_lister(**lister_args):
    GNULister(**lister_args).run()


@app.task(name=__name__ + '.ping')
def ping():
    return 'OK'
