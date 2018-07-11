# Copyright (C) 2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import random

from celery import group

from ..core.tasks import ListerTaskBase, RangeListerTask
from .lister import GitLabLister


class GitLabListerTask(ListerTaskBase):
    def new_lister(self, api_baseurl='https://gitlab.com/api/v4',
                   instance='gitlab.com'):
        return GitLabLister(api_baseurl=api_baseurl, instance=instance)


class RangeGitLabLister(GitLabListerTask, RangeListerTask):
    """GitLab lister working on specified range (start, end) arguments.

    """
    task_queue = 'swh_lister_gitlab_refresh'


class FullGitLabRelister(GitLabListerTask):
    task_queue = 'swh_lister_gitlab_refresh'

    def run_task(self, *args, **kwargs):
        lister = self.new_lister(*args, **kwargs)
        total, _, per_page = lister.get_pages_information()

        ranges = []
        prev_index = None
        for index in range(0, total, per_page):
            if index is not None and prev_index is not None:
                ranges.append((prev_index, index))
            prev_index = index

        random.shuffle(ranges)
        range_task = RangeGitLabLister()
        group(range_task.s(minv, maxv, *args, **kwargs)
              for minv, maxv in ranges)()
