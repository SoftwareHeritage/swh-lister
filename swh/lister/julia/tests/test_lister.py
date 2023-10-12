# Copyright (C) 2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from pathlib import Path

from swh.lister.julia.lister import JuliaLister
from swh.lister.julia.tests import prepare_repository_from_archive

expected_origins = [
    "https://github.com/leios/Fable.jl.git",
    "https://github.com/oscar-system/Oscar.jl.git",
]


def test_julia_get_registry_repository(datadir, tmp_path, swh_scheduler):
    archive_path = Path(datadir, "fake-julia-registry-repository.tar.gz")
    repo_url = prepare_repository_from_archive(archive_path, "General", tmp_path)

    lister = JuliaLister(url=repo_url, scheduler=swh_scheduler)
    assert not lister.REPO_PATH.exists()

    lister.get_registry_repository()
    assert lister.REPO_PATH.exists()
    # ensure get_registry_repository is idempotent
    lister.get_registry_repository()
    assert lister.REPO_PATH.exists()

    # ensure the repository is deleted once the lister has run
    lister.run()
    assert not lister.REPO_PATH.exists()


def test_julia_lister(datadir, tmp_path, swh_scheduler):
    archive_path = Path(datadir, "fake-julia-registry-repository.tar.gz")
    repo_url = prepare_repository_from_archive(archive_path, "General", tmp_path)
    lister = JuliaLister(url=repo_url, scheduler=swh_scheduler)
    lister.REPO_PATH = Path(tmp_path, "General")
    lister.REGISTRY_PATH = lister.REPO_PATH / "Registry.toml"

    res = lister.run()
    assert res.origins == 1 + 1

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    assert len(scheduler_origins) == len(expected_origins)
    assert {
        (
            scheduled.visit_type,
            scheduled.url,
            scheduled.last_update,
        )
        for scheduled in scheduler_origins
    } == {("git", expected, None) for expected in expected_origins}
