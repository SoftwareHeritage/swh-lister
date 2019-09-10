# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.scheduler.celery_backend.config import app
from swh.lister.phabricator.lister import PhabricatorLister


@app.task(name=__name__ + '.FullPhabricatorLister')
def list_phabricator_full(**lister_args):
    'Full update of a Phabricator instance'
    PhabricatorLister(**lister_args).run()


@app.task(name=__name__ + '.ping')
def _ping():
    return 'OK'
