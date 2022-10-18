# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from celery import shared_task

from swh.lister.hackage.lister import HackageLister


@shared_task(name=__name__ + ".HackageListerTask")
def list_hackage(**lister_args):
    """Lister task for Hackage, the Haskell Package Repository"""
    return HackageLister.from_configfile(**lister_args).run().dict()


@shared_task(name=__name__ + ".ping")
def _ping():
    return "OK"
