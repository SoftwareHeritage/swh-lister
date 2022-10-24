# Copyright (C) 2018-2022 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging

from ..gogs.lister import GogsLister

logger = logging.getLogger(__name__)


class GiteaLister(GogsLister):
    """List origins from Gitea.

    Gitea API documentation: https://try.gitea.io/api/swagger

    The API does pagination and provides navigation URLs through the 'Link' header.
    The default value for page size is the maximum value observed on the instances
    accessible at https://try.gitea.io/api/v1/ and https://codeberg.org/api/v1/."""

    LISTER_NAME = "gitea"
