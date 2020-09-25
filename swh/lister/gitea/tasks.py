# Copyright (C) 2020 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import random

from celery import group, shared_task

from .. import utils
from .lister import GiteaLister

NBPAGES = 10


@shared_task(name=__name__ + ".IncrementalGiteaLister")
def list_gitea_incremental(**lister_args):
    """Incremental update of a Gitea instance"""
    lister_args["order"] = "desc"
    lister = GiteaLister(**lister_args)
    total_pages = lister.get_pages_information()[1]
    # stopping as soon as existing origins for that instance are detected
    return lister.run(min_bound=1, max_bound=total_pages, check_existence=True)


@shared_task(name=__name__ + ".RangeGiteaLister")
def _range_gitea_lister(start, end, **lister_args):
    lister = GiteaLister(**lister_args)
    return lister.run(min_bound=start, max_bound=end)


@shared_task(name=__name__ + ".FullGiteaRelister", bind=True)
def list_gitea_full(self, **lister_args):
    """Full update of a Gitea instance"""
    lister = GiteaLister(**lister_args)
    _, total_pages, _ = lister.get_pages_information()
    ranges = list(utils.split_range(total_pages, NBPAGES))
    random.shuffle(ranges)
    promise = group(
        _range_gitea_lister.s(minv, maxv, **lister_args) for minv, maxv in ranges
    )()
    self.log.debug("%s OK (spawned %s subtasks)" % (self.name, len(ranges)))
    try:
        promise.save()
    except (NotImplementedError, AttributeError):
        self.log.info("Unable to call save_group with current result backend.")
    # FIXME: what to do in terms of return here?
    return promise.id


@shared_task(name=__name__ + ".ping")
def _ping():
    return "OK"
