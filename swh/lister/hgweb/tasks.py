# Copyright (C) 2026  The Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Dict

from celery import shared_task

from .lister import HgwebLister


@shared_task(name=f"{__name__}.HgwebListerTask")
def list_hgweb(**lister_args) -> Dict[str, str]:
    """Lister task for Hgweb instances"""
    lister = HgwebLister.from_configfile(**lister_args)
    return lister.run().dict()
