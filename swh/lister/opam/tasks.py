# Copyright (C) 2021 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from celery import shared_task

from swh.lister.opam.lister import OpamLister


@shared_task(name=__name__ + ".OpamListerTask")
def list_opam(**lister_args):
    """Lister task for the Opam registry"""
    return OpamLister.from_configfile(**lister_args).run().dict()


@shared_task(name=__name__ + ".ping")
def _ping():
    return "OK"
