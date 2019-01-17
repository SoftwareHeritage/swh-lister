# Copyright (C) 2017-2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.scheduler.celery_backend.config import app

from .lister import DebianLister


@app.task(name=__name__ + '.DebianListerTask')
def debian_lister(distribution, **lister_args):
    DebianLister(**lister_args).run(distribution)


@app.task(name=__name__ + '.ping')
def ping():
    return 'OK'
