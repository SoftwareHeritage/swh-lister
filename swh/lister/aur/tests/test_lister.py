# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import gzip
import json
import os

from swh.lister.aur.lister import AurLister

expected_origins = [
    {
        "visit_type": "aur",
        "url": "https://aur.archlinux.org/packages/hg-evolve",
        "git_url": "https://aur.archlinux.org/hg-evolve.git",
        "extra_loader_arguments": {
            "artifacts": [
                {
                    "filename": "hg-evolve.tar.gz",
                    "url": "https://aur.archlinux.org/cgit/aur.git/snapshot/hg-evolve.tar.gz",  # noqa: B950
                    "version": "10.5.1-1",
                }
            ],
            "aur_metadata": [
                {
                    "version": "10.5.1-1",
                    "project_url": "https://www.mercurial-scm.org/doc/evolution/",
                    "last_update": "2022-04-27T20:02:56+00:00",
                    "pkgname": "hg-evolve",
                }
            ],
        },
    },
    {
        "visit_type": "aur",
        "url": "https://aur.archlinux.org/packages/ibus-git",
        "git_url": "https://aur.archlinux.org/ibus-git.git",
        "extra_loader_arguments": {
            "artifacts": [
                {
                    "filename": "ibus-git.tar.gz",
                    "url": "https://aur.archlinux.org/cgit/aur.git/snapshot/ibus-git.tar.gz",  # noqa: B950
                    "version": "1.5.23+12+gef4c5c7e-1",
                }
            ],
            "aur_metadata": [
                {
                    "version": "1.5.23+12+gef4c5c7e-1",
                    "project_url": "https://github.com/ibus/ibus/wiki",
                    "last_update": "2021-02-08T06:12:11+00:00",
                    "pkgname": "ibus-git",
                }
            ],
        },
    },
    {
        "visit_type": "aur",
        "url": "https://aur.archlinux.org/packages/libervia-web-hg",
        "git_url": "https://aur.archlinux.org/libervia-web-hg.git",
        "extra_loader_arguments": {
            "artifacts": [
                {
                    "filename": "libervia-web-hg.tar.gz",
                    "url": "https://aur.archlinux.org/cgit/aur.git/snapshot/libervia-web-hg.tar.gz",  # noqa: B950
                    "version": "0.9.0.r1492.3a34d78f2717-1",
                }
            ],
            "aur_metadata": [
                {
                    "version": "0.9.0.r1492.3a34d78f2717-1",
                    "project_url": "http://salut-a-toi.org/",
                    "last_update": "2022-02-26T15:30:58+00:00",
                    "pkgname": "libervia-web-hg",
                }
            ],
        },
    },
    {
        "visit_type": "aur",
        "url": "https://aur.archlinux.org/packages/tealdeer-git",
        "git_url": "https://aur.archlinux.org/tealdeer-git.git",
        "extra_loader_arguments": {
            "artifacts": [
                {
                    "filename": "tealdeer-git.tar.gz",
                    "url": "https://aur.archlinux.org/cgit/aur.git/snapshot/tealdeer-git.tar.gz",  # noqa: B950
                    "version": "r255.30b7c5f-1",
                }
            ],
            "aur_metadata": [
                {
                    "version": "r255.30b7c5f-1",
                    "project_url": "https://github.com/dbrgn/tealdeer",
                    "last_update": "2020-09-04T20:36:52+00:00",
                    "pkgname": "tealdeer-git",
                }
            ],
        },
    },
]


def test_aur_lister(datadir, swh_scheduler, requests_mock):
    lister = AurLister(scheduler=swh_scheduler)

    packages_index_filename = "packages-meta-v1.json.gz"

    # simulate requests behavior: gzip and deflate transfer-encodings are automatically decoded
    with gzip.open(os.path.join(datadir, packages_index_filename), "rb") as f:
        requests_mock.get(
            f"{lister.BASE_URL}/{packages_index_filename}", json=json.loads(f.read())
        )

    res = lister.run()

    assert res.pages == 4
    assert res.origins == 8
    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    aur_origins = [origin for origin in scheduler_origins if origin.visit_type == "aur"]
    git_origins = [origin for origin in scheduler_origins if origin.visit_type == "git"]

    assert [
        (
            scheduled.visit_type,
            scheduled.url,
            scheduled.extra_loader_arguments["artifacts"],
        )
        for scheduled in sorted(aur_origins, key=lambda scheduled: scheduled.url)
    ] == [
        (
            "aur",
            expected["url"],
            expected["extra_loader_arguments"]["artifacts"],
        )
        for expected in sorted(expected_origins, key=lambda expected: expected["url"])
    ]

    assert {origin.url for origin in git_origins} == {
        origin["git_url"] for origin in expected_origins
    }
