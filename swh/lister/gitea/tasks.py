# Copyright (C) 2020-2022 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Dict

from celery import shared_task

from .lister import GiteaLister


@shared_task(name=__name__ + ".FullGiteaRelister")
def list_gitea_full(**lister_args) -> Dict[str, int]:
    """Full update of a Gitea instance"""
    lister = GiteaLister.from_configfile(**lister_args)
    return lister.run().dict()


@shared_task(name=__name__ + ".ping")
def _ping() -> str:
    return "OK"
