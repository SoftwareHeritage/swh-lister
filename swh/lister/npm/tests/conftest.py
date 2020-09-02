# Copyright (C) 2019-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest


@pytest.fixture
def lister_under_test():
    return "npm"


@pytest.fixture
def lister_npm(swh_lister):
    # Add the load-npm in the scheduler backend
    swh_lister.scheduler.create_task_type(
        {
            "type": "load-npm",
            "description": "Load npm package",
            "backend_name": "swh.loader.package.tasks.LoadNpm",
            "default_interval": "1 day",
        }
    )

    return swh_lister
