# Copyright (C) 2023 The Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


def register():
    from .lister import GitwebLister

    return {
        "lister": GitwebLister,
        "task_modules": [f"{__name__}.tasks"],
    }
