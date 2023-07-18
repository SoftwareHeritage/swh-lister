# Copyright (C) 2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from celery import shared_task

from swh.lister.dlang.lister import DlangLister


@shared_task(name=__name__ + ".DlangListerTask")
def list_dlang(**lister_args):
    """Lister task for D lang packages registry"""
    return DlangLister.from_configfile(**lister_args).run().dict()


@shared_task(name=__name__ + ".ping")
def _ping():
    return "OK"
