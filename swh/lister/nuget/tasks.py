# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from celery import shared_task

from swh.lister.nuget.lister import NugetLister


@shared_task(name=__name__ + ".NugetListerTask")
def list_nuget(**lister_args):
    """Lister task for Nuget (Javascript package manager) registry"""
    return NugetLister.from_configfile(**lister_args).run().dict()


@shared_task(name=__name__ + ".ping")
def _ping():
    return "OK"
