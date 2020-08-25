# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from celery import shared_task

from .lister import PackagistLister


@shared_task(name=__name__ + ".PackagistListerTask")
def list_packagist(**lister_args):
    "List the packagist (php) registry"
    PackagistLister(**lister_args).run()


@shared_task(name=__name__ + ".ping")
def _ping():
    return "OK"
