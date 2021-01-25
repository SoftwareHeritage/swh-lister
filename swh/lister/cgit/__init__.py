# Copyright (C) 2019-2021 The Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


def register():
    from .lister import CGitLister

    return {
        "lister": CGitLister,
        "task_modules": ["%s.tasks" % __name__],
    }
