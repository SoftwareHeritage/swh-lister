# Copyright (C) 2023 The Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Dict

from celery import shared_task

from .lister import GitilesLister


@shared_task(name=f"{__name__}.GitilesListerTask")
def list_gitiles(**lister_args) -> Dict[str, str]:
    """Lister task for Gitiles instances"""
    lister = GitilesLister.from_configfile(**lister_args)
    return lister.run().dict()
