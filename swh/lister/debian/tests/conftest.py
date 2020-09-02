# Copyright (C) 2019-2020 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest

from pytest_postgresql.janitor import DatabaseJanitor
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from swh.lister.core.models import SQLBase
from swh.lister.debian import debian_init


@pytest.fixture
def lister_debian(swh_listers):
    lister = swh_listers["debian"]

    # Initialize the debian data model
    debian_init(lister.db_engine, suites=["stretch"], components=["main", "contrib"])

    # Add the load-deb-package in the scheduler backend
    lister.scheduler.create_task_type(
        {
            "type": "load-deb-package",
            "description": "Load a Debian package",
            "backend_name": "swh.loader.debian.tasks.LoaderDebianPackage",
            "default_interval": "1 day",
        }
    )

    return lister


@pytest.fixture
def sqlalchemy_engine(postgresql_proc):
    pg_host = postgresql_proc.host
    pg_port = postgresql_proc.port
    pg_user = postgresql_proc.user

    pg_db = "sqlalchemy-tests"

    url = f"postgresql://{pg_user}@{pg_host}:{pg_port}/{pg_db}"
    with DatabaseJanitor(pg_user, pg_host, pg_port, pg_db, postgresql_proc.version):
        engine = create_engine(url)
        yield engine
        engine.dispose()


@pytest.fixture
def session(sqlalchemy_engine):
    SQLBase.metadata.create_all(sqlalchemy_engine)
    Session = sessionmaker(bind=sqlalchemy_engine)
    session = Session()
    yield session
    session.close()
