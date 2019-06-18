# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.scheduler.celery_backend.config import app
from swh.lister.phabricator.lister import PhabricatorLister


def new_lister(forge_url='https://forge.softwareheritage.org', instance='swh',
               api_token=None, **kw):
    return PhabricatorLister(
        forge_url=forge_url, instance=instance, api_token=api_token, **kw)


@app.task(name=__name__ + '.FullPhabricatorLister')
def full_phabricator_lister(**lister_args):
    lister = new_lister(**lister_args)
    lister.run()


@app.task(name=__name__ + '.ping')
def ping():
    return 'OK'
