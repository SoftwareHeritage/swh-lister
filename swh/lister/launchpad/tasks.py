# Copyright (C) 2020-2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from celery import shared_task

from .lister import LaunchpadLister


@shared_task(name=__name__ + ".ping")
def _ping():
    return "OK"


@shared_task(name=__name__ + ".FullLaunchpadLister")
def list_launchpad_full(**lister_args):
    """Full listing of git repositories hosted on Launchpad"""
    lister = LaunchpadLister.from_configfile(**lister_args)
    return lister.run().dict()


@shared_task(name=__name__ + ".IncrementalLaunchpadLister")
def list_launchpad_incremental(**lister_args):
    """Incremental listing of git repositories hosted on Launchpad"""
    lister = LaunchpadLister.from_configfile(**lister_args, incremental=True)
    return lister.run().dict()
