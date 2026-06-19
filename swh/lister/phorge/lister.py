# Copyright (C) 2018-2026  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging

from ..phabricator.lister import PhabricatorLister

logger = logging.getLogger(__name__)


class PhorgeLister(PhabricatorLister):
    """
    List all repositories hosted on a Phorge instance.

    Args:
        url: base URL of a Phorge instance
            (for instance https://we.phorge.it/)
        instance: string identifier for the listed forge,
            URL network location will be used if not provided
        api_token: authentication token for Conduit API
    """

    LISTER_NAME = "phorge"
