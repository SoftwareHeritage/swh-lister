# Copyright (C) 2019-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest


@pytest.fixture
def lister_under_test():
    return "cran"


@pytest.fixture
def lister_cran(swh_lister):
    swh_lister.scheduler.create_task_type(
        {
            "type": "load-cran",
            "description": "Load a CRAN package",
            "backend_name": "swh.loader.package.cran.tasks.LoaderCRAN",
            "default_interval": "1 day",
        }
    )

    return swh_lister
