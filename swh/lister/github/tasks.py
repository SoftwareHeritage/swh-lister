# Copyright (C) 2017-2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import random
from typing import Dict, Optional

from celery import group, shared_task

from swh.lister.github.lister import GitHubLister

GROUP_SPLIT = 100000


@shared_task(name=__name__ + ".IncrementalGitHubLister")
def list_github_incremental() -> Dict[str, int]:
    "Incremental update of GitHub"
    lister = GitHubLister.from_configfile()
    return lister.run().dict()


@shared_task(name=__name__ + ".RangeGitHubLister")
def _range_github_lister(first_id: int, last_id: int) -> Dict[str, int]:
    lister = GitHubLister.from_configfile(first_id=first_id, last_id=last_id)
    return lister.run().dict()


@shared_task(name=__name__ + ".FullGitHubRelister", bind=True)
def list_github_full(self, split: Optional[int] = None) -> str:
    """Full update of GitHub

    It's not to be called for an initial listing.

    """
    lister = GitHubLister.from_configfile()
    last_index = lister.state.last_seen_id

    bounds = list(range(0, last_index + 1, split or GROUP_SPLIT))
    if bounds[-1] != last_index:
        bounds.append(last_index)

    ranges = list(zip(bounds[:-1], bounds[1:]))
    random.shuffle(ranges)
    promise = group(
        _range_github_lister.s(first_id=minv, last_id=maxv) for minv, maxv in ranges
    )()
    self.log.debug("%s OK (spawned %s subtasks)" % (self.name, len(ranges)))
    try:
        promise.save()  # so that we can restore the GroupResult in tests
    except (NotImplementedError, AttributeError):
        self.log.info("Unable to call save_group with current result backend.")
    # FIXME: what to do in terms of return here?
    return promise.id


@shared_task(name=__name__ + ".ping")
def _ping() -> str:
    return "OK"
