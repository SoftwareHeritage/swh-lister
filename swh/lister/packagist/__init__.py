# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


def register():
    from .lister import PackagistLister
    from .models import PackagistModel

    return {
        "models": [PackagistModel],
        "lister": PackagistLister,
        "task_modules": ["%s.tasks" % __name__],
    }
