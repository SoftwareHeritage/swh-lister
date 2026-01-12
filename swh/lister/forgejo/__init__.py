# Copyright (C) 2020-2026 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


def register():
    from .lister import ForgejoLister

    return {
        "lister": ForgejoLister,
        "task_modules": ["%s.tasks" % __name__],
    }
