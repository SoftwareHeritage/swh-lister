# Copyright (C) 2026  The Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Dict

from celery import shared_task

from .lister import GerritLister


@shared_task(name=f"{__name__}.GerritListerTask")
def list_gerrit(**lister_args) -> Dict[str, str]:
    """Lister task for Gerrit instances"""
    lister = GerritLister.from_configfile(**lister_args)
    return lister.run().dict()
