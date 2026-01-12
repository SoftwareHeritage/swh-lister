# Copyright (C) 2018-2023 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging

from ..gitlab.lister import GitLabLister, Repository

logger = logging.getLogger(__name__)


class HeptapodLister(GitLabLister):
    """List origins from Heptapod.

    Same as the GitLab API except for the vcs_type field.
    """

    LISTER_NAME = "heptapod"

    VCS_MAPPING = {"hg_git": "hg"}

    def _get_visit_type(self, repo: Repository) -> str:
        vcs: str = repo["vcs_type"]
        return self.VCS_MAPPING.get(vcs, vcs)
