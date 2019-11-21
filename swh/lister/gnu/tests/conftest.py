# Copyright (C) 2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest

from swh.lister.core.tests.conftest import *  # noqa


@pytest.fixture
def lister_gnu(swh_listers):
    lister = swh_listers['gnu']

    # Add the load-deb-package in the scheduler backend
    lister.scheduler.create_task_type({
        'type': 'load-archive-files',
        'description': 'Load archive files',
        'backend_name': 'swh.loader.package.tasks.LoadArchive',
        'default_interval': '1 day',
    })

    return lister
