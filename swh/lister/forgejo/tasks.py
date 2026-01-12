# Copyright (C) 2020-2026 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Dict

from celery import shared_task

from .lister import ForgejoLister


@shared_task(name=__name__ + ".FullForgejoRelister")
def list_forgejo_full(**lister_args) -> Dict[str, int]:
    """Full update of a Forgejo instance"""
    lister = ForgejoLister.from_configfile(**lister_args)
    return lister.run().dict()


@shared_task(name=__name__ + ".ping")
def _ping() -> str:
    return "OK"
