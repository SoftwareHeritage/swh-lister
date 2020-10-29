# Copyright (C) 2019-2020 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os

import pytest
from sqlalchemy.orm import sessionmaker

from swh.core.db.pytest_plugin import postgresql_fact

from swh.lister.debian import debian_init
import swh.scheduler

SQL_DIR = os.path.join(os.path.dirname(swh.scheduler.__file__), "sql")
postgresql_scheduler = postgresql_fact(
    "postgresql_proc",
    db_name="scheduler-lister",
    dump_files=os.path.join(SQL_DIR, "*.sql"),
    # do not truncate the task tables, it's required in between test
    no_truncate_tables={"dbversion", "priority_ratio", "task"},
)


@pytest.fixture
def swh_scheduler_config(postgresql_scheduler):
    return {"db": postgresql_scheduler.dsn}


@pytest.fixture
def lister_under_test():
    return "debian"


@pytest.fixture
def lister_debian(swh_lister):
    # Initialize the debian data model
    debian_init(
        swh_lister.db_engine, suites=["stretch"], components=["main", "contrib"]
    )

    # Add the load-deb-package in the scheduler backend
    swh_lister.scheduler.create_task_type(
        {
            "type": "load-deb-package",
            "description": "Load a Debian package",
            "backend_name": "swh.loader.packages.debian.tasks.LoaderDebianPackage",
            "default_interval": "1 day",
        }
    )

    return swh_lister


@pytest.fixture
def session(lister_db_url, engine):
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()
