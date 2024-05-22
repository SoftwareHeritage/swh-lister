# Copyright (C) 2024  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from celery import shared_task

from swh.lister.save_bulk.lister import SaveBulkLister


@shared_task(name=__name__ + ".SaveBulkListerTask")
def list_save_bulk(**kwargs):
    """Task for save-bulk lister"""
    return SaveBulkLister.from_configfile(**kwargs).run().dict()


@shared_task(name=__name__ + ".ping")
def _ping():
    return "OK"
