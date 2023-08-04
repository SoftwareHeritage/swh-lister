# Copyright (C) 2018-2023 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from celery import shared_task

from .lister import PyPILister


@shared_task(name=f"{__name__}.PyPIListerTask")
def list_pypi(**lister_args):
    "Full listing of the PyPI registry"
    lister = PyPILister.from_configfile(**lister_args)
    return lister.run().dict()


@shared_task(name=__name__ + ".ping")
def _ping():
    return "OK"
