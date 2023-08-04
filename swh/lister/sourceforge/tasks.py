# Copyright (C) 2019-2023 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Dict

from celery import shared_task

from swh.lister.sourceforge.lister import SourceForgeLister


@shared_task(name=__name__ + ".FullSourceForgeLister")
def list_sourceforge_full(**lister_args) -> Dict[str, int]:
    """Full update of a SourceForge instance"""
    return SourceForgeLister.from_configfile(**lister_args).run().dict()


@shared_task(name=__name__ + ".IncrementalSourceForgeLister")
def list_sourceforge_incremental(**lister_args) -> Dict[str, int]:
    """Incremental update of a SourceForge instance"""
    return (
        SourceForgeLister.from_configfile(incremental=True, **lister_args).run().dict()
    )


@shared_task(name=__name__ + ".ping")
def _ping():
    return "OK"
