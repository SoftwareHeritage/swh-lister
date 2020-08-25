# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from celery import shared_task

from swh.lister.phabricator.lister import PhabricatorLister


@shared_task(name=__name__ + ".FullPhabricatorLister")
def list_phabricator_full(**lister_args):
    """Full update of a Phabricator instance"""
    return PhabricatorLister(**lister_args).run()


@shared_task(name=__name__ + ".ping")
def _ping():
    return "OK"
