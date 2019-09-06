# Copyright (C) 2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.scheduler.celery_backend.config import app

from .lister import PyPILister


@app.task(name=__name__ + '.PyPIListerTask')
def list_pypi(**lister_args):
    'Full update of the PyPI (python) registry'
    PyPILister(**lister_args).run()


@app.task(name=__name__ + '.ping')
def _ping():
    return 'OK'
