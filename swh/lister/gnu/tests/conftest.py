# Copyright (C) 2019-2020 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest


@pytest.fixture
def lister_under_test():
    return "gnu"


@pytest.fixture
def lister_gnu(swh_lister):
    for task_type in [
        {
            "type": "load-archive-files",
            "description": "Load archive repository",
            "backend_name": "swh.loader.packages.tasks.LoadArchive",
            "default_interval": "1 day",
        },
    ]:
        swh_lister.scheduler.create_task_type(task_type)

    return swh_lister
