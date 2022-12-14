# Copyright (C) 2022 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Dict

from celery import shared_task

from .lister import GogsLister


@shared_task(name=__name__ + ".FullGogsRelister")
def list_gogs_full(**lister_args) -> Dict[str, int]:
    """Full update of a Gogs instance"""
    lister = GogsLister.from_configfile(**lister_args)
    return lister.run().dict()


@shared_task(name=__name__ + ".ping")
def _ping() -> str:
    return "OK"
