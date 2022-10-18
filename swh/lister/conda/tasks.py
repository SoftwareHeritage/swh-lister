# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from celery import shared_task

from swh.lister.conda.lister import CondaLister


@shared_task(name=__name__ + ".CondaListerTask")
def list_conda(**lister_args):
    """Lister task for Anaconda registry"""
    return CondaLister.from_configfile(**lister_args).run().dict()


@shared_task(name=__name__ + ".ping")
def _ping():
    return "OK"
