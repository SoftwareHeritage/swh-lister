# Copyright (C) 2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import random

from celery import group, shared_task

from .. import utils
from .lister import GitLabLister

NBPAGES = 10


@shared_task(name=__name__ + ".IncrementalGitLabLister")
def list_gitlab_incremental(**lister_args):
    """Incremental update of a GitLab instance"""
    lister_args["sort"] = "desc"
    lister = GitLabLister(**lister_args)
    total_pages = lister.get_pages_information()[1]
    # stopping as soon as existing origins for that instance are detected
    return lister.run(min_bound=1, max_bound=total_pages, check_existence=True)


@shared_task(name=__name__ + ".RangeGitLabLister")
def _range_gitlab_lister(start, end, **lister_args):
    lister = GitLabLister(**lister_args)
    return lister.run(min_bound=start, max_bound=end)


@shared_task(name=__name__ + ".FullGitLabRelister", bind=True)
def list_gitlab_full(self, **lister_args):
    """Full update of a GitLab instance"""
    lister = GitLabLister(**lister_args)
    _, total_pages, _ = lister.get_pages_information()
    ranges = list(utils.split_range(total_pages, NBPAGES))
    random.shuffle(ranges)
    promise = group(
        _range_gitlab_lister.s(minv, maxv, **lister_args) for minv, maxv in ranges
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
