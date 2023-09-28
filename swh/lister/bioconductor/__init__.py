# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


def register():
    from .lister import BioconductorLister

    return {
        "lister": BioconductorLister,
        "task_modules": [f"{__name__}.tasks"],
    }
