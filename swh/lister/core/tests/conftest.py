# Copyright (C) 2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.scheduler.tests.conftest import *  # noqa

import logging
import pytest

from sqlalchemy import create_engine

from swh.lister import get_lister, SUPPORTED_LISTERS
from swh.lister.core.models import initialize


logger = logging.getLogger(__name__)


@pytest.fixture
def swh_listers(request, postgresql_proc, postgresql, swh_scheduler):
    db_url = 'postgresql://{user}@{host}:{port}/{dbname}'.format(
            host=postgresql_proc.host,
            port=postgresql_proc.port,
            user='postgres',
            dbname='tests')

    logger.debug('lister db_url: %s', db_url)

    listers = {}

    # Prepare schema for all listers
    for lister_name in SUPPORTED_LISTERS:
        lister = get_lister(lister_name, db_url=db_url)
        lister.scheduler = swh_scheduler  # inject scheduler fixture
        listers[lister_name] = lister
    initialize(create_engine(db_url), drop_tables=True)

    # Add the load-archive-files expected by some listers (gnu, cran, ...)
    swh_scheduler.create_task_type({
        'type': 'load-archive-files',
        'description': 'Load archive files.',
        'backend_name': 'swh.loader.package.tasks.LoadArchive',
        'default_interval': '1 day',
    })

    return listers
