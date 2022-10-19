# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest

from swh.lister.conda.lister import CondaLister


@pytest.fixture
def expected_origins():
    return [
        {
            "url": "https://anaconda.org/conda-forge/21cmfast",
            "artifacts": [
                {
                    "url": "https://conda.anaconda.org/conda-forge/linux-64/21cmfast-3.0.2-py36h1af98f8_1.tar.bz2",  # noqa: B950
                    "date": "2020-11-11T16:04:49.658000+00:00",
                    "version": "linux-64/3.0.2-py36h1af98f8_1",
                    "filename": "21cmfast-3.0.2-py36h1af98f8_1.tar.bz2",
                    "checksums": {
                        "md5": "d65ab674acf3b7294ebacaec05fc5b54",
                        "sha256": "1154fceeb5c4ee9bb97d245713ac21eb1910237c724d2b7103747215663273c2",  # noqa: B950
                    },
                }
            ],
        },
        {
            "url": "https://anaconda.org/conda-forge/lifetimes",
            "artifacts": [
                {
                    "url": "https://conda.anaconda.org/conda-forge/linux-64/lifetimes-0.11.1-py36h9f0ad1d_1.tar.bz2",  # noqa: B950
                    "date": "2020-07-06T12:19:36.425000+00:00",
                    "version": "linux-64/0.11.1-py36h9f0ad1d_1",
                    "filename": "lifetimes-0.11.1-py36h9f0ad1d_1.tar.bz2",
                    "checksums": {
                        "md5": "faa398f7ba0d60ce44aa6eeded490cee",
                        "sha256": "f82a352dfae8abceeeaa538b220fd9c5e4aa4e59092a6a6cea70b9ec0581ea03",  # noqa: B950
                    },
                },
                {
                    "url": "https://conda.anaconda.org/conda-forge/linux-64/lifetimes-0.11.1-py36hc560c46_1.tar.bz2",  # noqa: B950
                    "date": "2020-07-06T12:19:37.032000+00:00",
                    "version": "linux-64/0.11.1-py36hc560c46_1",
                    "filename": "lifetimes-0.11.1-py36hc560c46_1.tar.bz2",
                    "checksums": {
                        "md5": "c53a689a4c5948e84211bdfc23e3fe68",
                        "sha256": "76146c2ebd6e3b65928bde53a2585287759d77beba785c0eeb889ee565c0035d",  # noqa: B950
                    },
                },
            ],
        },
    ]


def test_conda_lister_free_channel(datadir, requests_mock_datadir, swh_scheduler):
    lister = CondaLister(
        scheduler=swh_scheduler, channel="free", archs=["linux-64", "osx-64", "win-64"]
    )
    res = lister.run()

    assert res.pages == 3
    assert res.origins == 11


def test_conda_lister_conda_forge_channel(
    requests_mock_datadir, swh_scheduler, expected_origins
):
    lister = CondaLister(
        scheduler=swh_scheduler,
        url="https://conda.anaconda.org",
        channel="conda-forge",
        archs=["linux-64"],
    )
    res = lister.run()

    assert res.pages == 1
    assert res.origins == 2

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    assert len(scheduler_origins) == len(expected_origins)

    assert [
        (
            scheduled.visit_type,
            scheduled.url,
            scheduled.extra_loader_arguments["artifacts"],
        )
        for scheduled in sorted(scheduler_origins, key=lambda scheduled: scheduled.url)
    ] == [
        (
            "conda",
            expected["url"],
            expected["artifacts"],
        )
        for expected in sorted(expected_origins, key=lambda expected: expected["url"])
    ]


def test_conda_lister_number_of_yielded_origins(
    requests_mock_datadir, swh_scheduler, expected_origins
):
    """Check that a single ListedOrigin instance is sent by expected origins."""
    lister = CondaLister(
        scheduler=swh_scheduler,
        url="https://conda.anaconda.org",
        channel="conda-forge",
        archs=["linux-64"],
    )

    listed_origins = []
    for page in lister.get_pages():
        listed_origins += list(lister.get_origins_from_page(page))

    assert sorted([listed_origin.url for listed_origin in listed_origins]) == sorted(
        [origin["url"] for origin in expected_origins]
    )
