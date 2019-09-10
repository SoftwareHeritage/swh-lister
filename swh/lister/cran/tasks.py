# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.scheduler.celery_backend.config import app

from swh.lister.cran.lister import CRANLister


@app.task(name=__name__ + '.CRANListerTask')
def list_cran(**lister_args):
    '''Lister task for the CRAN registry'''
    CRANLister(**lister_args).run()


@app.task(name=__name__ + '.ping')
def _ping():
    return 'OK'
