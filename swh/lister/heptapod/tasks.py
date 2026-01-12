# Copyright (C) 2018-2021 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from celery import shared_task

from swh.lister.heptapod.lister import HeptapodLister


@shared_task(name=__name__ + ".IncrementalHeptapodLister")
def list_heptapod_incremental(**lister_args):
    """Incremental update of a Heptapod instance"""
    lister = HeptapodLister.from_configfile(incremental=True, **lister_args)
    return lister.run().dict()


@shared_task(name=__name__ + ".FullHeptapodRelister")
def list_heptapod_full(**lister_args):
    """Full update of a Heptapod instance"""
    lister = HeptapodLister.from_configfile(incremental=False, **lister_args)
    return lister.run().dict()


@shared_task(name=__name__ + ".ping")
def _ping():
    return "OK"
