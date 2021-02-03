# Copyright (C) 2020-2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os

pytest_plugins = ["swh.scheduler.pytest_plugin"]

os.environ["LC_ALL"] = "C.UTF-8"
