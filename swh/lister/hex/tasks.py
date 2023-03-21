# Copyright (C) 2022 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Dict, Optional

from celery import shared_task

from .lister import HexLister


@shared_task(name=__name__ + ".HexListerTask")
def list_hex_full(
    instance: Optional[str] = None,
) -> Dict[str, int]:
    """Lister task for Hex.pm"""
    lister = HexLister.from_configfile(instance=instance)
    return lister.run().dict()


@shared_task(name=__name__ + ".ping")
def _ping() -> str:
    return "OK"
