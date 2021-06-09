# Copyright (C) 2021 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Dict

from celery import shared_task

from .lister import TuleapLister


@shared_task(name=__name__ + ".FullTuleapLister")
def list_tuleap_full(**lister_args) -> Dict[str, int]:
    """Full update of a Tuleap instance"""
    lister = TuleapLister.from_configfile(**lister_args)
    return lister.run().dict()


@shared_task(name=__name__ + ".ping")
def _ping() -> str:
    return "OK"
