# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from celery import shared_task

from swh.lister.cran.lister import CRANLister


@shared_task(name=__name__ + ".CRANListerTask")
def list_cran(**lister_args):
    """Lister task for the CRAN registry"""
    return CRANLister.from_configfile(**lister_args).run().dict()


@shared_task(name=__name__ + ".ping")
def _ping():
    return "OK"
