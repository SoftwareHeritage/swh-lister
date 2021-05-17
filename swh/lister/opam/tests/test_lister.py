# Copyright (C) 2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import io
from unittest.mock import MagicMock

from swh.lister.opam.lister import OpamLister


def test_urls(swh_scheduler, mocker):

    instance_url = "https://opam.ocaml.org"

    lister = OpamLister(swh_scheduler, url=instance_url, instance="opam")

    mocked_popen = MagicMock()
    mocked_popen.stdout = io.BytesIO(b"bar\nbaz\nfoo\n")

    # replaces the real Popen with a fake one
    mocker.patch("swh.lister.opam.lister.Popen", return_value=mocked_popen)

    # call the lister and get all listed origins urls
    stats = lister.run()

    assert stats.pages == 3
    assert stats.origins == 3

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    expected_urls = [
        f"opam+{instance_url}/packages/bar/",
        f"opam+{instance_url}/packages/baz/",
        f"opam+{instance_url}/packages/foo/",
    ]

    result_urls = [origin.url for origin in scheduler_origins]

    assert expected_urls == result_urls


def test_opam_binary(datadir, swh_scheduler):

    instance_url = f"file://{datadir}/fake_opam_repo"

    lister = OpamLister(swh_scheduler, url=instance_url, instance="fake")

    stats = lister.run()

    assert stats.pages == 4
    assert stats.origins == 4

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    expected_urls = [
        f"opam+{instance_url}/packages/agrid/",
        f"opam+{instance_url}/packages/calculon/",
        f"opam+{instance_url}/packages/directories/",
        f"opam+{instance_url}/packages/ocb/",
    ]

    result_urls = [origin.url for origin in scheduler_origins]

    assert expected_urls == result_urls
