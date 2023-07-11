# Copyright (C) 2023 The Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Dict

from celery import shared_task

from .lister import GitwebLister


@shared_task(name=f"{__name__}.GitwebListerTask")
def list_gitweb(**lister_args) -> Dict[str, str]:
    """Lister task for Gitweb instances"""
    lister = GitwebLister.from_configfile(**lister_args)
    return lister.run().dict()
