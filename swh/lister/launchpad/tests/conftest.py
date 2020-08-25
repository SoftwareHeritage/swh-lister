from swh.lister.core.tests.conftest import *  # noqa
from datetime import datetime
import json
import os
from unittest.mock import patch
import pytest
from swh.lister import get_lister
from swh.lister.core.models import initialize
from sqlalchemy.engine import create_engine


@pytest.fixture
def lister_launchpad(datadir, lister_db_url, swh_scheduler):
    class Collection:
        entries = []

        def __init__(self, file):
            self.entries = [Repo(r) for r in file]

        def __getitem__(self, key):
            return self.entries[key]

    class Repo:
        def __init__(self, d: dict):
            for key in d.keys():
                if key == "date_last_modified":
                    setattr(self, key, datetime.fromisoformat(d[key]))
                else:
                    setattr(self, key, d[key])

    def mock_lp_response(page) -> Collection:
        response_filepath = os.path.join(datadir, f"response{page}.json")
        with open(response_filepath, "r", encoding="utf-8") as f:
            return Collection(json.load(f))

    with patch("launchpadlib.launchpad.Launchpad.login_anonymously"):
        lister = get_lister("launchpad", db_url=lister_db_url)

    lister.scheduler = swh_scheduler  # inject scheduler fixture
    lister.launchpad.git_repositories.getRepositories.side_effect = [
        mock_lp_response(i) for i in range(3)
    ]

    initialize(create_engine(lister_db_url), drop_tables=True)

    return lister
