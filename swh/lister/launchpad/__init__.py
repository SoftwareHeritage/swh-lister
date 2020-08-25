# Copyright (C) 2020 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


def register():
    from .models import LaunchpadModel
    from .lister import LaunchpadLister

    return {
        "models": [LaunchpadModel],
        "lister": LaunchpadLister,
        "task_modules": ["%s.tasks" % __name__],
    }
