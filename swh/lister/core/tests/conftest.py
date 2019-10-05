from swh.scheduler.tests.conftest import *  # noqa

import pytest

from sqlalchemy import create_engine

from swh.lister import get_lister, SUPPORTED_LISTERS
from swh.lister.core.models import initialize


@pytest.fixture
def swh_listers(request, postgresql_proc, postgresql, swh_scheduler):
    db_url = 'postgresql://{user}@{host}:{port}/{dbname}'.format(
            host=postgresql_proc.host,
            port=postgresql_proc.port,
            user='postgres',
            dbname='tests')

    listers = {}

    # Prepare schema for all listers
    for lister_name in SUPPORTED_LISTERS:
        lister = get_lister(lister_name, db_url=db_url)
        lister.scheduler = swh_scheduler  # inject scheduler fixture
        listers[lister_name] = lister
    initialize(create_engine(db_url), drop_tables=True)

    return listers
