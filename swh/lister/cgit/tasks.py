# Copyright (C) 2019 The Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Dict

from celery import shared_task

from .lister import CGitLister


@shared_task(name=__name__ + ".CGitListerTask")
def list_cgit(**lister_args) -> Dict[str, str]:
    """Lister task for CGit instances"""
    lister = CGitLister.from_configfile(**lister_args)
    return lister.run().dict()


@shared_task(name=__name__ + ".ping")
def _ping():
    return "OK"
