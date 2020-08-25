# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from celery import shared_task

from .lister import GNULister


@shared_task(name=__name__ + ".GNUListerTask")
def list_gnu_full(**lister_args):
    """List lister for the GNU source code archive"""
    return GNULister(**lister_args).run()


@shared_task(name=__name__ + ".ping")
def _ping():
    return "OK"
