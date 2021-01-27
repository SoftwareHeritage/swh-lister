# Copyright (C) 2018-2021 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from celery import shared_task

from swh.lister.gitlab.lister import GitLabLister


@shared_task(name=__name__ + ".IncrementalGitLabLister")
def list_gitlab_incremental(**lister_args):
    """Incremental update of a GitLab instance"""
    lister = GitLabLister.from_configfile(incremental=True, **lister_args)
    return lister.run().dict()


@shared_task(name=__name__ + ".FullGitLabRelister")
def list_gitlab_full(**lister_args):
    """Full update of a GitLab instance"""
    lister = GitLabLister.from_configfile(incremental=False, **lister_args)
    return lister.run().dict()


@shared_task(name=__name__ + ".ping")
def _ping():
    return "OK"
