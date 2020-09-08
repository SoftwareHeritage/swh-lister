# Copyright (C) 2019-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest


@pytest.fixture
def lister_under_test():
    return "pypi"


@pytest.fixture
def lister_pypi(swh_lister):
    # Add the load-pypi in the scheduler backend
    swh_lister.scheduler.create_task_type(
        {
            "type": "load-pypi",
            "description": "Load PyPI package",
            "backend_name": "swh.loader.package.tasks.LoadPyPI",
            "default_interval": "1 day",
        }
    )

    return swh_lister
