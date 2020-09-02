# Copyright (C) 2019-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging

import pytest

from sqlalchemy import create_engine

from swh.lister import get_lister, SUPPORTED_LISTERS
from swh.lister.core.models import initialize


logger = logging.getLogger(__name__)


@pytest.fixture
def lister_db_url(postgresql_proc, postgresql):
    db_url = "postgresql://{user}@{host}:{port}/{dbname}".format(
        host=postgresql_proc.host,
        port=postgresql_proc.port,
        user="postgres",
        dbname="tests",
    )
    logger.debug("lister db_url: %s", db_url)
    return db_url


@pytest.fixture
def listers_to_instantiate():
    """Fixture to define what listers to instantiate. Because some need dedicated setup.

    """
    return set(SUPPORTED_LISTERS) - {"launchpad"}


@pytest.fixture
def swh_listers(
    mock_get_scheduler, lister_db_url, swh_scheduler, listers_to_instantiate
):
    listers = {}

    # Prepare schema for all listers
    for lister_name in listers_to_instantiate:
        lister = get_lister(lister_name, db_url=lister_db_url)
        listers[lister_name] = lister
    initialize(create_engine(lister_db_url), drop_tables=True)

    # Add the load-archive-files expected by some listers (gnu, cran, ...)
    swh_scheduler.create_task_type(
        {
            "type": "load-archive-files",
            "description": "Load archive files.",
            "backend_name": "swh.loader.package.tasks.LoadArchive",
            "default_interval": "1 day",
        }
    )

    return listers
