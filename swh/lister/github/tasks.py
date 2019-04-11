# Copyright (C) 2017-2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import random

from celery import group
from swh.scheduler.celery_backend.config import app

from swh.lister.github.lister import GitHubLister

GROUP_SPLIT = 10000


def new_lister(api_baseurl='https://api.github.com', **kw):
    return GitHubLister(api_baseurl=api_baseurl, **kw)


@app.task(name=__name__ + '.IncrementalGitHubLister')
def incremental_github_lister(**lister_args):
    lister = new_lister(**lister_args)
    lister.run(min_bound=lister.db_last_index(), max_bound=None)


@app.task(name=__name__ + '.RangeGitHubLister')
def range_github_lister(start, end, **lister_args):
    lister = new_lister(**lister_args)
    lister.run(min_bound=start, max_bound=end)


@app.task(name=__name__ + '.FullGitHubRelister', bind=True)
def full_github_relister(self, split=None, **lister_args):
    lister = new_lister(**lister_args)
    ranges = lister.db_partition_indices(split or GROUP_SPLIT)
    random.shuffle(ranges)
    promise = group(range_github_lister.s(minv, maxv, **lister_args)
                    for minv, maxv in ranges)()
    self.log.debug('%s OK (spawned %s subtasks)' % (self.name, len(ranges)))
    try:
        promise.save()  # so that we can restore the GroupResult in tests
    except (NotImplementedError, AttributeError):
        self.log.info('Unable to call save_group with current result backend.')
    return promise.id


@app.task(name=__name__ + '.ping')
def ping():
    return 'OK'
