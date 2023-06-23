# Copyright (C) 2023 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Dict

from celery import shared_task

from .lister import PagureLister


@shared_task(name=__name__ + ".PagureListerTask")
def list_pagure(**lister_args) -> Dict[str, int]:
    "List git repositories hosted on a pagure forge."
    lister = PagureLister.from_configfile(**lister_args)
    return lister.run().dict()


@shared_task(name=__name__ + ".ping")
def _ping() -> str:
    return "OK"
