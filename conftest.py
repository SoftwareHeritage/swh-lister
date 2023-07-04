# Copyright (C) 2020-2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os

import pytest

pytest_plugins = ["swh.scheduler.pytest_plugin", "swh.core.github.pytest_plugin"]

os.environ["LC_ALL"] = "C.UTF-8"


@pytest.fixture(autouse=True)
def tenacity_wait(mocker):
    # Stops tenacity from blocking lister tests for 50x errors
    from swh.lister.pattern import Lister

    mocker.patch.object(Lister.http_request.retry, "sleep")
