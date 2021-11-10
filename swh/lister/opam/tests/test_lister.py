# Copyright (C) 2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import io
import os
from tempfile import mkdtemp
from unittest.mock import MagicMock

import pytest

from swh.lister.opam.lister import OpamLister, opam_init

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


def test_mock_init_repository_init(mock_opam, tmp_path, datadir):
    """Initializing opam root directory with an instance should be ok

    """
    mock_init, mock_popen = mock_opam

    instance = "fake"
    instance_url = f"file://{datadir}/{instance}"
    opam_root = str(tmp_path / "test-opam")
    assert not os.path.exists(opam_root)

    # This will initialize an opam directory with the instance
    opam_init(opam_root, instance, instance_url, {})

    assert mock_init.called


def test_mock_init_repository_update(mock_opam, tmp_path, datadir):
    """Updating opam root directory with another instance should be ok

    """
    mock_init, mock_popen = mock_opam

    instance = "fake_opam_repo"
    instance_url = f"file://{datadir}/{instance}"
    opam_root = str(tmp_path / "test-opam")

    os.makedirs(opam_root, exist_ok=True)
    with open(os.path.join(opam_root, "opam"), "w") as f:
        f.write("one file to avoid empty folder")

    assert os.path.exists(opam_root)
    assert os.listdir(opam_root) == ["opam"]  # not empty
    # This will update the repository opam with another instance
    opam_init(opam_root, instance, instance_url, {})

    assert mock_init.called


def test_lister_opam_optional_instance(swh_scheduler):
    """Instance name should be optional and default to be built out of the netloc."""
    netloc = "opam.ocaml.org"
    instance_url = f"https://{netloc}"

    lister = OpamLister(swh_scheduler, url=instance_url,)
    assert lister.instance == netloc
    assert lister.opam_root == "/tmp/opam/"


def test_urls(swh_scheduler, mock_opam, tmp_path):
    mock_init, mock_popen = mock_opam
    instance_url = "https://opam.ocaml.org"
    tmp_folder = mkdtemp(dir=tmp_path, prefix="swh_opam_lister")

    lister = OpamLister(
        swh_scheduler, url=instance_url, instance="opam", opam_root=tmp_folder,
    )
    assert lister.instance == "opam"
    assert lister.opam_root == tmp_folder

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


def test_opam_binary(datadir, swh_scheduler, tmp_path):
    instance_url = f"file://{datadir}/fake_opam_repo"

    lister = OpamLister(
        swh_scheduler,
        url=instance_url,
        instance="fake",
        opam_root=mkdtemp(dir=tmp_path, prefix="swh_opam_lister"),
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


def test_opam_multi_instance(datadir, swh_scheduler, tmp_path):
    instance_url = f"file://{datadir}/fake_opam_repo"

    lister = OpamLister(
        swh_scheduler,
        url=instance_url,
        instance="fake",
        opam_root=mkdtemp(dir=tmp_path, prefix="swh_opam_lister"),
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
