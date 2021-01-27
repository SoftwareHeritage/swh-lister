# Copyright (C) 2020 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Dict, Optional

from celery import shared_task

from .lister import GiteaLister


@shared_task(name=__name__ + ".FullGiteaRelister")
def list_gitea_full(
    url: str,
    instance: Optional[str] = None,
    api_token: Optional[str] = None,
    page_size: Optional[int] = None,
) -> Dict[str, int]:
    """Full update of a Gitea instance"""
    lister = GiteaLister.from_configfile(
        url=url, instance=instance, api_token=api_token, page_size=page_size
    )
    return lister.run().dict()


@shared_task(name=__name__ + ".ping")
def _ping() -> str:
    return "OK"
