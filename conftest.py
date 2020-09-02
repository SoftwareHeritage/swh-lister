# Copyright (C) 2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os

import pytest

pytest_plugins = ["swh.scheduler.pytest_plugin", "swh.lister.pytest_plugin"]

os.environ["LC_ALL"] = "C.UTF-8"


@pytest.fixture
def mock_get_scheduler(monkeypatch, swh_scheduler):
    """Override the get_scheduler function in swh.lister.core.lister_base, to
    return the swh_scheduler fixture.
    """
    from swh.lister.core import lister_base

    # Match the signature from swh.scheduler.get_scheduler
    def get_scheduler(cls, args={}):
        return swh_scheduler

    monkeypatch.setattr(lister_base, "get_scheduler", get_scheduler)

    yield monkeypatch
