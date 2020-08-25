# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from celery import shared_task

from .lister import CGitLister


@shared_task(name=__name__ + ".CGitListerTask")
def list_cgit(**lister_args):
    """Lister task for CGit instances"""
    return CGitLister(**lister_args).run()


@shared_task(name=__name__ + ".ping")
def _ping():
    return "OK"
