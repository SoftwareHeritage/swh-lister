# Copyright (C) 2022 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from celery import shared_task

from .lister import GolangLister


@shared_task(name=__name__ + ".FullGolangLister")
def list_golang(**lister_args):
    "List the Golang module registry"
    return GolangLister.from_configfile(**lister_args).run().dict()


@shared_task(name=__name__ + ".ping")
def _ping():
    return "OK"
