# Copyright (C) 2017-2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.lister.core.tasks import (IndexingDiscoveryListerTask,
                                   RangeListerTask,
                                   IndexingRefreshListerTask, ListerTaskBase)

from .lister import GitHubLister


class GitHubListerTask(ListerTaskBase):
    def new_lister(self):
        return GitHubLister(lister_name='github.com',
                            api_baseurl='https://api.github.com')


class IncrementalGitHubLister(GitHubListerTask, IndexingDiscoveryListerTask):
    task_queue = 'swh_lister_github_discover'


class RangeGitHubLister(GitHubListerTask, RangeListerTask):
    task_queue = 'swh_lister_github_refresh'


class FullGitHubRelister(GitHubListerTask, IndexingRefreshListerTask):
    task_queue = 'swh_lister_github_refresh'
