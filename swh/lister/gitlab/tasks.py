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
    """Range GitLab lister (list available origins on specified range)

    """
    task_queue = 'swh_lister_gitlab_refresh'


class FullGitLabRelister(GitLabListerTask):
    """Full GitLab lister (list all available origins from the api).

    """
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


class IncrementalGitLabLister(ListerTaskBase):
    """Incremental GitLab lister (list only new available origins).

    """
    task_queue = 'swh_lister_gitlab_discover'

    def new_lister(self, api_baseurl='https://gitlab.com/api/v4',
                   instance='gitlab.com'):
        # assuming going forward in desc order, page 1 through <x-total-pages>
        return GitLabLister(instance=instance, api_baseurl=api_baseurl,
                            sort='desc')

    def run_task(self, *args, **kwargs):
        lister = self.new_lister(*args, **kwargs)
        total, _, _ = lister.get_pages_information()
        # stopping as soon as existing origins for that instance are detected
        return lister.run(min_bound=1, max_bound=total, check_existence=True)
