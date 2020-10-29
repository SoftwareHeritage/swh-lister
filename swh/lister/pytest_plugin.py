# Copyright (C) 2019-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging
import os

import pytest
from sqlalchemy import create_engine
import yaml

from swh.lister import SUPPORTED_LISTERS, get_lister
from swh.lister.core.models import initialize

logger = logging.getLogger(__name__)


@pytest.fixture
def lister_db_url(postgresql):
    db_params = postgresql.get_dsn_parameters()
    db_url = "postgresql://{user}@{host}:{port}/{dbname}".format(**db_params)
    logger.debug("lister db_url: %s", db_url)
    return db_url


@pytest.fixture
def lister_under_test():
    """Fixture to determine which lister to test"""
    return "core"


@pytest.fixture
def swh_lister_config(lister_db_url, swh_scheduler_config):
    return {
        "scheduler": {"cls": "local", **swh_scheduler_config},
        "lister": {"cls": "local", "args": {"db": lister_db_url},},
        "credentials": {},
        "cache_responses": False,
    }


@pytest.fixture(autouse=True)
def swh_config(swh_lister_config, monkeypatch, tmp_path):
    conf_path = os.path.join(str(tmp_path), "lister.yml")
    with open(conf_path, "w") as f:
        f.write(yaml.dump(swh_lister_config))
    monkeypatch.setenv("SWH_CONFIG_FILENAME", conf_path)
    return conf_path


@pytest.fixture
def engine(lister_db_url):
    engine = create_engine(lister_db_url)
    initialize(engine, drop_tables=True)
    return engine


@pytest.fixture
def swh_lister(engine, lister_db_url, lister_under_test, swh_config):
    assert lister_under_test in SUPPORTED_LISTERS
    return get_lister(lister_under_test, db_url=lister_db_url)
