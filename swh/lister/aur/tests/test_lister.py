# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information
from swh.lister.aur.lister import AurLister

expected_origins = [
    {
        "visit_type": "aur",
        "url": "https://aur.archlinux.org/hg-evolve.git",
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
        "url": "https://aur.archlinux.org/ibus-git.git",
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
        "url": "https://aur.archlinux.org/libervia-web-hg.git",
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
        "url": "https://aur.archlinux.org/tealdeer-git.git",
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


def test_aur_lister(datadir, requests_mock_datadir, swh_scheduler):
    lister = AurLister(scheduler=swh_scheduler)
    res = lister.run()

    assert res.pages == 4
    assert res.origins == 4

    scheduler_origins_sorted = sorted(
        swh_scheduler.get_listed_origins(lister.lister_obj.id).results,
        key=lambda x: x.url,
    )
    expected_origins_sorted = sorted(expected_origins, key=lambda x: x.get("url"))

    assert len(scheduler_origins_sorted) == len(expected_origins_sorted)

    assert [
        (
            scheduled.visit_type,
            scheduled.url,
            scheduled.extra_loader_arguments.get("artifacts"),
        )
        for scheduled in scheduler_origins_sorted
    ] == [
        (
            "aur",
            expected.get("url"),
            expected.get("extra_loader_arguments").get("artifacts"),
        )
        for expected in expected_origins_sorted
    ]


def test_aur_lister_directory_cleanup(datadir, requests_mock_datadir, swh_scheduler):
    lister = AurLister(scheduler=swh_scheduler)
    lister.run()
    # Repository directory should not exists after the lister runs
    assert not lister.DESTINATION_PATH.exists()
