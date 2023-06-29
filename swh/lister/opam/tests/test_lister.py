# Copyright (C) 2021-2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os
import shutil
from subprocess import CalledProcessError
from tempfile import mkdtemp

import pytest

from swh.lister.opam.lister import OpamLister, opam_init

module_name = "swh.lister.opam.lister"

opam_path = shutil.which("opam")


@pytest.fixture
def mock_opam(mocker):
    """Fixture to bypass the actual opam calls within the test context."""

    # replaces the real Popen with a fake one (list origins command)
    completed_process = mocker.MagicMock()
    completed_process.stdout = "bar\nbaz\nfoo\n"

    # inhibits the real calls to `subprocess.run` which prepare the required
    # internal opam state then list all packages
    mock_opam = mocker.patch(
        f"{module_name}.run", side_effect=[None, completed_process]
    )
    return mock_opam


def test_mock_init_repository_init(mock_opam, tmp_path, datadir):
    """Initializing opam root directory with an instance should be ok"""
    instance = "fake"
    instance_url = f"file://{datadir}/{instance}"
    opam_root = str(tmp_path / "test-opam")
    assert not os.path.exists(opam_root)

    # This will initialize an opam directory with the instance
    opam_init(opam_root, instance, instance_url, {})

    assert mock_opam.called


def test_mock_init_repository_update(mock_opam, tmp_path, datadir):
    """Updating opam root directory with another instance should be ok"""
    instance = "fake_opam_repo"
    instance_url = f"http://example.org/{instance}"
    opam_root = str(tmp_path / "test-opam")

    os.makedirs(opam_root, exist_ok=True)
    with open(os.path.join(opam_root, "opam"), "w") as f:
        f.write("one file to avoid empty folder")

    assert os.path.exists(opam_root)
    assert os.listdir(opam_root) == ["opam"]  # not empty
    # This will update the repository opam with another instance
    opam_init(opam_root, instance, instance_url, {})

    assert mock_opam.called


def test_lister_opam_optional_instance(swh_scheduler):
    """Instance name should be optional and default to be built out of the netloc."""
    netloc = "opam.ocaml.org"
    instance_url = f"https://{netloc}"

    lister = OpamLister(
        swh_scheduler,
        url=instance_url,
    )
    assert lister.instance == netloc
    assert lister.opam_root == "/tmp/opam/"


def test_urls(swh_scheduler, mock_opam, tmp_path):
    instance_url = "https://opam.ocaml.org"
    tmp_folder = mkdtemp(dir=tmp_path, prefix="swh_opam_lister")

    lister = OpamLister(
        swh_scheduler,
        url=instance_url,
        instance="opam",
        opam_root=tmp_folder,
    )
    assert lister.instance == "opam"
    assert lister.opam_root == tmp_folder

    # call the lister and get all listed origins urls
    stats = lister.run()

    assert mock_opam.call_count == 2

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


@pytest.mark.skipif(opam_path is None, reason="opam binary is missing")
def test_opam_binary(datadir, swh_scheduler, tmp_path, mocker):
    from swh.lister.opam.lister import opam_init

    instance_url = "http://example.org/fake_opam_repo"

    def mock_opam_init(opam_root, instance, url, env):
        assert url == instance_url
        return opam_init(opam_root, instance, f"{datadir}/fake_opam_repo", env)

    # Patch opam_init to use the local directory
    mocker.patch("swh.lister.opam.lister.opam_init", side_effect=mock_opam_init)

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


@pytest.mark.skipif(opam_path is None, reason="opam binary is missing")
def test_opam_multi_instance(datadir, swh_scheduler, tmp_path, mocker):
    from swh.lister.opam.lister import opam_init

    instance_url = "http://example.org/fake_opam_repo"

    def mock_opam_init(opam_root, instance, url, env):
        assert url == instance_url
        return opam_init(opam_root, instance, f"{datadir}/fake_opam_repo", env)

    # Patch opam_init to use the local directory
    mocker.patch("swh.lister.opam.lister.opam_init", side_effect=mock_opam_init)

    opam_root = mkdtemp(dir=tmp_path, prefix="swh_opam_lister")

    def check_listing():
        lister = OpamLister(
            swh_scheduler,
            url=instance_url,
            instance="fake",
            opam_root=opam_root,
        )

        stats = lister.run()

        assert stats.pages == 4
        assert stats.origins == 4

        scheduler_origins = swh_scheduler.get_listed_origins(
            lister.lister_obj.id
        ).results

        expected_urls = [
            f"opam+{instance_url}/packages/agrid/",
            f"opam+{instance_url}/packages/calculon/",
            f"opam+{instance_url}/packages/directories/",
            f"opam+{instance_url}/packages/ocb/",
        ]

        result_urls = [origin.url for origin in scheduler_origins]

        assert expected_urls == result_urls

    # first listing
    check_listing()
    # check second listing works as expected
    check_listing()


def test_opam_init_failure(swh_scheduler, mocker, tmp_path):
    instance = "fake_opam_repo"
    instance_url = f"http://example.org/{instance}"
    opam_root = str(tmp_path / "test-opam")

    mock_opam = mocker.patch(
        f"{module_name}.run",
        side_effect=CalledProcessError(returncode=1, cmd="opam init"),
    )

    lister = OpamLister(
        swh_scheduler,
        url=instance_url,
        instance=instance,
        opam_root=opam_root,
    )

    with pytest.raises(CalledProcessError, match="opam init"):
        lister.run()

    assert mock_opam.called


def test_opam_list_failure(swh_scheduler, mocker, tmp_path):
    instance = "fake_opam_repo"
    instance_url = f"http://example.org/{instance}"
    opam_root = str(tmp_path / "test-opam")

    mock_opam = mocker.patch(
        f"{module_name}.run",
        side_effect=[None, CalledProcessError(returncode=1, cmd="opam list")],
    )

    lister = OpamLister(
        swh_scheduler,
        url=instance_url,
        instance=instance,
        opam_root=opam_root,
    )

    with pytest.raises(CalledProcessError, match="opam list"):
        lister.run()

    assert mock_opam.call_count == 2
