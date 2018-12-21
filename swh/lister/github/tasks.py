# Copyright (C) 2017-2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import random

from celery import group

from swh.scheduler.celery_backend.config import app
from swh.scheduler.task import SWHTask

from swh.lister.github.lister import GitHubLister

GROUP_SPLIT = 10000


def new_lister(api_baseurl='https://api.github.com', **kw):
    return GitHubLister(api_baseurl=api_baseurl, **kw)


@app.task(name='swh.lister.github.tasks.IncrementalGitHubLister',
          base=SWHTask, bind=True)
def incremental_github_lister(self, **lister_args):
    self.log.debug('%s, lister_args=%s' % (
        self.name, lister_args))
    lister = new_lister(**lister_args)
    lister.run(min_bound=lister.db_last_index(), max_bound=None)
    self.log.debug('%s OK' % (self.name))


@app.task(name='swh.lister.github.tasks.RangeGitHubLister',
          base=SWHTask, bind=True)
def range_github_lister(self, start, end, **lister_args):
    self.log.debug('%s(start=%s, end=%d), lister_args=%s' % (
        self.name, start, end, lister_args))
    lister = new_lister(**lister_args)
    lister.run(min_bound=start, max_bound=end)
    self.log.debug('%s OK' % (self.name))


@app.task(name='swh.lister.github.tasks.FullGitHubRelister',
          base=SWHTask, bind=True)
def full_github_relister(self, split=None, **lister_args):
    self.log.debug('%s, lister_args=%s' % (
        self.name, lister_args))
    lister = new_lister(**lister_args)
    ranges = lister.db_partition_indices(split or GROUP_SPLIT)
    random.shuffle(ranges)
    group(range_github_lister.s(minv, maxv, **lister_args)
          for minv, maxv in ranges)()
    self.log.debug('%s OK (spawned %s subtasks)' % (self.name, len(ranges)))


@app.task(name='swh.lister.github.tasks.ping',
          base=SWHTask, bind=True)
def ping(self):
    self.log.debug(self.name)
    return 'OK'
