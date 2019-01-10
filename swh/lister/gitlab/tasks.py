# Copyright (C) 2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import random

from celery import group

from swh.scheduler.celery_backend.config import app

from .. import utils
from .lister import GitLabLister


NBPAGES = 10


def new_lister(api_baseurl='https://gitlab.com/api/v4',
               instance=None, sort='asc', per_page=20):
    return GitLabLister(
        api_baseurl=api_baseurl, instance=instance, sort=sort,
        per_page=per_page)


@app.task(name='swh.lister.gitlab.tasks.IncrementalGitLabLister',
          bind=True)
def incremental_gitlab_lister(self, **lister_args):
    self.log.debug('%s, lister_args=%s' % (
        self.name, lister_args))
    lister_args['sort'] = 'desc'
    lister = new_lister(**lister_args)
    total_pages = lister.get_pages_information()[1]
    # stopping as soon as existing origins for that instance are detected
    lister.run(min_bound=1, max_bound=total_pages, check_existence=True)
    self.log.debug('%s OK' % (self.name))


@app.task(name='swh.lister.gitlab.tasks.RangeGitLabLister',
          bind=True)
def range_gitlab_lister(self, start, end, **lister_args):
    self.log.debug('%s(start=%s, end=%d), lister_args=%s' % (
        self.name, start, end, lister_args))
    lister = new_lister(**lister_args)
    lister.run(min_bound=start, max_bound=end)
    self.log.debug('%s OK' % (self.name))


@app.task(name='swh.lister.gitlab.tasks.FullGitLabRelister',
          bind=True)
def full_gitlab_relister(self, **lister_args):
    self.log.debug('%s, lister_args=%s' % (
        self.name, lister_args))
    lister = new_lister(**lister_args)
    _, total_pages, _ = lister.get_pages_information()
    ranges = list(utils.split_range(total_pages, NBPAGES))
    random.shuffle(ranges)
    promise = group(range_gitlab_lister.s(minv, maxv, **lister_args)
                    for minv, maxv in ranges)()
    self.log.debug('%s OK (spawned %s subtasks)' % (self.name, len(ranges)))
    promise.save()
    return promise.id


@app.task(name='swh.lister.gitlab.tasks.ping',
          bind=True)
def ping(self):
    self.log.debug(self.name)
    return 'OK'
