# Copyright (C) 2019-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest


@pytest.fixture
def lister_under_test():
    return "phabricator"


@pytest.fixture
def lister_phabricator(swh_lister):
    # Amend the credentials
    swh_lister.config = {
        "cache_responses": False,
        "credentials": {"phabricator": {swh_lister.instance: [{"password": "foo"}]}},
    }
    swh_lister.scheduler.create_task_type(
        {
            "type": "load-git",
            "description": "Load git repository",
            "backend_name": "swh.loader.git.tasks.UpdateGitRepository",
            "default_interval": "1 day",
        }
    )

    return swh_lister
