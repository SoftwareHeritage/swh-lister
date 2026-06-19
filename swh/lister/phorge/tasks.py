# Copyright (C) 2019-2026  The Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Dict, Optional

from celery import shared_task

from swh.lister.phorge.lister import PhorgeLister


@shared_task(name=__name__ + ".FullPhorgeLister")
def list_phorge_full(
    url: str, instance: str, api_token: Optional[str] = None
) -> Dict[str, int]:
    """Full update of a Phorge instance"""
    return (
        PhorgeLister.from_configfile(url=url, instance=instance, api_token=api_token)
        .run()
        .dict()
    )


@shared_task(name=__name__ + ".ping")
def _ping():
    return "OK"
