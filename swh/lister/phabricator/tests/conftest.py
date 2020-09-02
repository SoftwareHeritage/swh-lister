# Copyright (C) 2019-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest


@pytest.fixture
def lister_phabricator(swh_listers):
    lister = swh_listers["phabricator"]

    # Amend the credentials
    lister.config = {
        "cache_responses": False,
        "credentials": {"phabricator": {lister.instance: [{"password": "foo"}]}},
    }

    return lister
