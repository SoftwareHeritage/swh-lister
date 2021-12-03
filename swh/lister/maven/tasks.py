# Copyright (C) 2021 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Dict

from celery import shared_task

from .lister import MavenLister


@shared_task(name=__name__ + ".FullMavenLister")
def list_maven_full(**lister_args) -> Dict[str, int]:
    """Full update of a Maven repository instance"""
    lister = MavenLister.from_configfile(incremental=False, **lister_args)
    return lister.run().dict()


@shared_task(name=__name__ + ".IncrementalMavenLister")
def list_maven_incremental(**lister_args) -> Dict[str, int]:
    """Incremental update of a Maven repository instance"""
    lister = MavenLister.from_configfile(incremental=True, **lister_args)
    return lister.run().dict()


@shared_task(name=__name__ + ".ping")
def _ping() -> str:
    return "OK"
