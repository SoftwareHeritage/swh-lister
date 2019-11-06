# Copyright (C) 2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest

from swh.lister.core.tests.conftest import *  # noqa


@pytest.fixture
def lister_packagist(swh_listers):
    lister = swh_listers['packagist']

    # Amend the scheduler with an unknown yet load-packagist task type
    lister.scheduler.create_task_type({
        'type': 'load-packagist',
        'description': 'Load packagist origin',
        'backend_name': 'swh.loader.package.tasks.LoaderPackagist',
        'default_interval': '1 day',
    })

    return lister
