# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from celery import shared_task


@shared_task(name=__name__ + ".NixGuixListerTask")
def list_nixguix(**lister_args):
    """Lister task for Arch Linux"""
    from swh.lister.nixguix.lister import NixGuixLister

    return NixGuixLister.from_configfile(**lister_args).run().dict()
