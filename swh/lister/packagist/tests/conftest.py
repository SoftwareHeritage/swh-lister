# Copyright (C) 2019-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest


@pytest.fixture
def lister_under_test():
    return "packagist"


@pytest.fixture
def lister_packagist(swh_lister):
    # Amend the scheduler with an unknown yet load-packagist task type
    swh_lister.scheduler.create_task_type(
        {
            "type": "load-packagist",
            "description": "Load packagist origin",
            "backend_name": "swh.loader.package.tasks.LoaderPackagist",
            "default_interval": "1 day",
        }
    )

    return swh_lister
