# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.scheduler.celery_backend.config import app

from .lister import CGitLister


def new_lister(url='https://git.kernel.org/',
               url_prefix=None,
               instance='kernal', **kw):
    return CGitLister(url=url, instance=instance, url_prefix=url_prefix,
                      **kw)


@app.task(name=__name__ + '.CGitListerTask')
def cgit_lister(**lister_args):
    lister = new_lister(**lister_args)
    lister.run()


@app.task(name=__name__ + '.ping')
def ping():
    return 'OK'
