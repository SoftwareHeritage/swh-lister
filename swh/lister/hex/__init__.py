# Copyright (C) 2022-2026  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


def register():
    from datetime import timedelta

    from .lister import HexLister

    return {
        "lister": HexLister,
        "task_modules": [f"{__name__}.tasks"],
        "task_types": {
            "list-hex-full": {
                "default_interval": timedelta(days=1),
                "min_interval": timedelta(days=1),
                "max_interval": timedelta(days=1),
            },
        },
    }
