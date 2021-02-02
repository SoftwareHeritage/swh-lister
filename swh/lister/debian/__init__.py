# Copyright (C) 2019-2021 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Any, Mapping


def register() -> Mapping[str, Any]:
    from .lister import DebianLister

    return {
        "lister": DebianLister,
        "task_modules": ["%s.tasks" % __name__],
    }
