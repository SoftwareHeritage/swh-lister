# Copyright (C) 2018-2021 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from celery import shared_task

from swh.lister.npm.lister import NpmLister


@shared_task(name=__name__ + ".NpmListerTask")
def list_npm_full(**lister_args):
    "Full lister for the npm (javascript) registry"
    lister = NpmLister.from_configfile(incremental=False, **lister_args)
    return lister.run().dict()


@shared_task(name=__name__ + ".NpmIncrementalListerTask")
def list_npm_incremental(**lister_args):
    "Incremental lister for the npm (javascript) registry"
    lister = NpmLister.from_configfile(incremental=True, **lister_args)
    return lister.run().dict()


@shared_task(name=__name__ + ".ping")
def _ping():
    return "OK"
