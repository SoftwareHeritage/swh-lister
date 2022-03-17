# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from celery import shared_task

from swh.lister.crates.lister import CratesLister


@shared_task(name=__name__ + ".CratesListerTask")
def list_crates(**lister_args):
    """Lister task for crates (rust) registry"""
    return CratesLister.from_configfile(**lister_args).run().dict()


@shared_task(name=__name__ + ".ping")
def _ping():
    return "OK"
