# Copyright (C) 2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import io
from tempfile import mkdtemp
from unittest.mock import MagicMock

import pytest

from swh.lister.opam.lister import OpamLister

module_name = "swh.lister.opam.lister"


@pytest.fixture
def mock_opam(mocker):
    """Fixture to bypass the actual opam calls within the test context.

    """
    # inhibits the real `subprocess.call` which prepares the required internal opam
    # state
    mock_init = mocker.patch(f"{module_name}.call", return_value=None)
    # replaces the real Popen with a fake one (list origins command)
    mocked_popen = MagicMock()
    mocked_popen.stdout = io.BytesIO(b"bar\nbaz\nfoo\n")
    mock_open = mocker.patch(f"{module_name}.Popen", return_value=mocked_popen)
    return mock_init, mock_open


def test_lister_opam_optional_instance(swh_scheduler):
    """Instance name should be optional and default to be built out of the netloc."""
    netloc = "opam.ocaml.org"
    instance_url = f"https://{netloc}"

    lister = OpamLister(swh_scheduler, url=instance_url,)
    assert lister.instance == netloc
    assert lister.opamroot.endswith(lister.instance)


def test_urls(swh_scheduler, mock_opam):
    mock_init, mock_popen = mock_opam

    instance_url = "https://opam.ocaml.org"

    lister = OpamLister(
        swh_scheduler,
        url=instance_url,
        instance="opam",
        opam_root=mkdtemp(prefix="swh_opam_lister"),
    )
    assert lister.instance == "opam"

    # call the lister and get all listed origins urls
    stats = lister.run()

    assert mock_init.called
    assert mock_popen.called

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

    lister = OpamLister(
        swh_scheduler,
        url=instance_url,
        instance="fake",
        opam_root=mkdtemp(prefix="swh_opam_lister"),
    )

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
