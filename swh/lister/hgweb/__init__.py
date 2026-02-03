# Copyright (C) 2026  The Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


def register():
    from .lister import HgwebLister

    return {
        "lister": HgwebLister,
        "task_modules": [f"{__name__}.tasks"],
    }
