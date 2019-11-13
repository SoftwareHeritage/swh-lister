# Copyright (C) 2019 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest

from swh.lister.core.tests.conftest import *  # noqa

from swh.lister.debian import debian_init


@pytest.fixture
def lister_debian(swh_listers):
    lister = swh_listers['debian']

    # Initialize the debian data model
    debian_init(lister.db_engine,
                distributions=['stretch'],
                area_names=['main', 'contrib'])

    # Add the load-deb-package in the scheduler backend
    lister.scheduler.create_task_type({
        'type': 'load-deb-package',
        'description': 'Load a Debian package',
        'backend_name': 'swh.loader.debian.tasks.LoaderDebianPackage',
        'default_interval': '1 day',
    })

    return lister
