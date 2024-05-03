# Copyright (C) 2019-2021 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


def register():
    from datetime import timedelta

    from .lister import NpmLister

    return {
        "lister": NpmLister,
        "task_modules": ["%s.tasks" % __name__],
        "task_types": {
            "list-npm-full": {
                "default_interval": timedelta(days=7),
                "min_interval": timedelta(days=7),
                "max_interval": timedelta(days=7),
            },
        },
    }
