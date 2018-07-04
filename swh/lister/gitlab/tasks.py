# Copyright (C) 2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.lister.core.tasks import ListerTaskBase, RangeListerTask


from .lister import GitLabLister


class GitLabDotComListerTask(ListerTaskBase):
    def new_lister(self, lister_name='gitlab.com',
                   api_baseurl='https://gitlab.com/api/v4'):
        return GitLabLister(
            lister_name=lister_name, api_baseurl=api_baseurl)


class RangeGitLabLister(GitLabDotComListerTask, RangeListerTask):
    """GitLab lister working on specified range (start, end) arguments.

    """
    task_queue = 'swh_lister_gitlab_refresh'


