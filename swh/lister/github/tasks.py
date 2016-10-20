# Copyright (C) 2016 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import random

from celery import group

from swh.scheduler.task import Task

from .lister import GitHubLister

GROUP_SPLIT = 10000


class IncrementalGitHubLister(Task):
    task_queue = 'swh_lister_github_incremental'

    def run(self):
        lister = GitHubLister()
        last_id = lister.last_repo_id()
        lister.fetch(min_id=last_id + 1, max_id=None)


class RangeGitHubLister(Task):
    task_queue = 'swh_lister_github_full'

    def run(self, start, end):
        lister = GitHubLister()
        lister.fetch(min_id=start, max_id=end)


class FullGitHubLister(Task):
    task_queue = 'swh_lister_github_full'

    def run(self):
        lister = GitHubLister()
        last_id = lister.last_repo_id()
        ranges = [
            (i, min(last_id, i + GROUP_SPLIT - 1))
            for i in range(1, last_id, GROUP_SPLIT)
        ]

        random.shuffle(ranges)

        range_task = RangeGitHubLister()
        group(range_task.s(min, max) for min, max in ranges)()
