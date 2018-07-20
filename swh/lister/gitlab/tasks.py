# Copyright (C) 2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import random

from celery import group

from .. import utils
from ..core.tasks import ListerTaskBase, RangeListerTask
from .lister import GitLabLister


class GitLabListerTask(ListerTaskBase):
    def new_lister(self, *, api_baseurl='https://gitlab.com/api/v4',
                   instance='gitlab', sort='asc', per_page=20):
        return GitLabLister(
            api_baseurl=api_baseurl, instance=instance, sort=sort)


class RangeGitLabLister(GitLabListerTask, RangeListerTask):
    """Range GitLab lister (list available origins on specified range)

    """
    task_queue = 'swh_lister_gitlab_refresh'


class FullGitLabRelister(GitLabListerTask):
    """Full GitLab lister (list all available origins from the api).

    """
    task_queue = 'swh_lister_gitlab_refresh'

    # nb pages
    nb_pages = 10

    def run_task(self, lister_args=None):
        if lister_args is None:
            lister_args = {}
        lister = self.new_lister(**lister_args)
        _, total_pages, _ = lister.get_pages_information()
        ranges = list(utils.split_range(total_pages, self.nb_pages))
        random.shuffle(ranges)
        range_task = RangeGitLabLister()
        group(range_task.s(minv, maxv, lister_args=lister_args)
              for minv, maxv in ranges)()


class IncrementalGitLabLister(GitLabListerTask):
    """Incremental GitLab lister (list only new available origins).

    """
    task_queue = 'swh_lister_gitlab_discover'

    def run_task(self, lister_args=None):
        if lister_args is None:
            lister_args = {}
        lister_args['sort'] = 'desc'
        lister = self.new_lister(**lister_args)
        _, total_pages, _ = lister.get_pages_information()
        # stopping as soon as existing origins for that instance are detected
        return lister.run(min_bound=1, max_bound=total_pages,
                          check_existence=True)
