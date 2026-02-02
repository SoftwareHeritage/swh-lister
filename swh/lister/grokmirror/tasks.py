# Copyright (C) 2026  The Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Dict

from celery import shared_task

from .lister import GrokmirrorLister


@shared_task(name=f"{__name__}.GrokmirrorListerTask")
def list_grokmirror(**lister_args) -> Dict[str, str]:
    """Lister task for Grokmirror instances"""
    lister = GrokmirrorLister.from_configfile(**lister_args)
    return lister.run().dict()
