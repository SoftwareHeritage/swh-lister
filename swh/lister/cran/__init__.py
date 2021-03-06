# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


def register():
    from .lister import CRANLister

    return {
        "models": [],
        "lister": CRANLister,
        "task_modules": ["%s.tasks" % __name__],
    }
