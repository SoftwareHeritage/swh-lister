# Copyright (C) 2019-2021 The Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Dict, Optional

from celery import shared_task

from .lister import CGitLister


@shared_task(name=__name__ + ".CGitListerTask")
def list_cgit(
    url: str, instance: Optional[str] = None, base_git_url: Optional[str] = None
) -> Dict[str, str]:
    """Lister task for CGit instances"""
    lister = CGitLister.from_configfile(
        url=url, instance=instance, base_git_url=base_git_url
    )
    return lister.run().dict()


@shared_task(name=__name__ + ".ping")
def _ping():
    return "OK"
