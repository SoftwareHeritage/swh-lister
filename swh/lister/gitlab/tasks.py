# Copyright (C) 2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import random

from celery import group

from .. import utils
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

    # nb pages
    nb_pages = 10

    def run_task(self, *args, **kwargs):
        lister = self.new_lister(*args, **kwargs)
        _, total_pages, _ = lister.get_pages_information()
        ranges = list(utils.split_range(total_pages, self.nb_pages))
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
        _, total_pages, _ = lister.get_pages_information()
        # stopping as soon as existing origins for that instance are detected
        return lister.run(min_bound=1, max_bound=total_pages,
                          check_existence=True)
