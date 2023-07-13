# Copyright (C) 2023 The Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Dict

from celery import shared_task

from .lister import StagitLister


@shared_task(name=f"{__name__}.StagitListerTask")
def list_stagit(**lister_args) -> Dict[str, str]:
    """Lister task for Stagit instances"""
    lister = StagitLister.from_configfile(**lister_args)
    return lister.run().dict()
