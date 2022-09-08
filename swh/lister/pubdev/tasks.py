# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from celery import shared_task

from swh.lister.pubdev.lister import PubDevLister


@shared_task(name=__name__ + ".PubDevListerTask")
def list_pubdev(**lister_args):
    """Lister task for pub.dev (Dart, Flutter) registry"""
    return PubDevLister.from_configfile(**lister_args).run().dict()


@shared_task(name=__name__ + ".ping")
def _ping():
    return "OK"
