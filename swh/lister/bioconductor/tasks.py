# Copyright (C) 2022-2023 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Dict

from celery import shared_task

from .lister import BioconductorLister


@shared_task(name=__name__ + ".BioconductorListerTask")
def list_bioconductor_full(**lister_args) -> Dict[str, int]:
    """Full listing of Bioconductor packages"""
    lister = BioconductorLister.from_configfile(**lister_args)
    return lister.run().dict()


@shared_task(name=__name__ + ".BioconductorIncrementalListerTask")
def list_bioconductor_incremental(**lister_args) -> Dict[str, int]:
    """Incremental listing of Bioconductor packages"""
    lister = BioconductorLister.from_configfile(**lister_args, incremental=True)
    return lister.run().dict()


@shared_task(name=__name__ + ".ping")
def _ping() -> str:
    return "OK"
