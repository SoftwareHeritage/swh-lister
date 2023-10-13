# Copyright (C) 2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from pathlib import Path

from dulwich import porcelain
import iso8601

from swh.lister.julia.lister import JuliaLister
from swh.lister.julia.tests import prepare_repository_from_archive

expected_origins_0 = {
    "https://github.com/leios/Fable.jl.git": "2001-01-02T17:18:19+00:00",
    "https://github.com/oscar-system/Oscar.jl.git": "2001-01-03T17:18:19+00:00",
}

expected_origins_1 = {
    "https://github.com/oscar-system/Oscar.jl.git": "2001-01-04T17:18:19+00:00",
    "https://github.com/serenity4/VulkanSpec.jl.git": "2001-01-05T17:18:19+00:00",
}


def test_julia_get_registry_repository(datadir, tmp_path, swh_scheduler):
    archive_path = Path(datadir, "fake-julia-registry-repository_0.tar.gz")
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
    archive_path = Path(datadir, "fake-julia-registry-repository_0.tar.gz")
    repo_url = prepare_repository_from_archive(archive_path, "General", tmp_path)
    lister = JuliaLister(url=repo_url, scheduler=swh_scheduler)
    lister.REPO_PATH = Path(tmp_path, "General")
    lister.REGISTRY_PATH = lister.REPO_PATH / "Registry.toml"

    res = lister.run()
    assert res.origins == len(expected_origins_0)

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    assert len(scheduler_origins) == len(expected_origins_0)

    assert {
        (
            scheduled.visit_type,
            scheduled.url,
            scheduled.last_update,
        )
        for scheduled in scheduler_origins
    } == {
        ("git", origin, iso8601.parse_date(last_update))
        for origin, last_update in expected_origins_0.items()
    }


def test_julia_lister_incremental(datadir, tmp_path, swh_scheduler):
    archive_path = Path(datadir, "fake-julia-registry-repository_0.tar.gz")
    repo_url = prepare_repository_from_archive(archive_path, "General", tmp_path)

    # Prepare first run
    lister = JuliaLister(url=repo_url, scheduler=swh_scheduler)
    lister.REPO_PATH = Path(tmp_path, "General")
    lister.REGISTRY_PATH = lister.REPO_PATH / "Registry.toml"
    # Latest Git commit hash expected
    with porcelain.open_repo_closing(lister.REPO_PATH) as r:
        expected_last_seen_commit = r.head().decode("ascii")

    assert expected_last_seen_commit is not None
    assert lister.state.last_seen_commit is None

    # First run
    res = lister.run()
    assert res.pages == 1
    assert res.origins == len(expected_origins_0)
    assert lister.state.last_seen_commit == expected_last_seen_commit

    scheduler_origins_0 = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    assert len(scheduler_origins_0) == len(expected_origins_0)
    assert {
        (
            scheduled.visit_type,
            scheduled.url,
            scheduled.last_update,
        )
        for scheduled in scheduler_origins_0
    } == {
        ("git", origin, iso8601.parse_date(last_update))
        for origin, last_update in expected_origins_0.items()
    }

    # Prepare second run
    archive_path = Path(datadir, "fake-julia-registry-repository_1.tar.gz")
    repo_url = prepare_repository_from_archive(archive_path, "General", tmp_path)

    lister = JuliaLister(url=repo_url, scheduler=swh_scheduler)
    lister.REPO_PATH = Path(tmp_path, "General")
    lister.REGISTRY_PATH = lister.REPO_PATH / "Registry.toml"

    assert lister.state.last_seen_commit == expected_last_seen_commit

    with porcelain.open_repo_closing(lister.REPO_PATH) as repo:
        new_expected_last_seen_commit = repo.head().decode("ascii")

    assert expected_last_seen_commit != new_expected_last_seen_commit

    # Second run
    res = lister.run()
    assert lister.state.last_seen_commit == new_expected_last_seen_commit
    assert res.pages == 1
    # One new package, one new version
    assert res.origins == len(expected_origins_1)

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    expected_origins = {**expected_origins_0, **expected_origins_1}
    assert len(scheduler_origins) == len(expected_origins)


def test_julia_lister_incremental_no_changes(datadir, tmp_path, swh_scheduler):
    archive_path = Path(datadir, "fake-julia-registry-repository_0.tar.gz")
    repo_url = prepare_repository_from_archive(archive_path, "General", tmp_path)
    lister = JuliaLister(url=repo_url, scheduler=swh_scheduler)
    lister.REPO_PATH = Path(tmp_path, "General")
    lister.REGISTRY_PATH = lister.REPO_PATH / "Registry.toml"

    # Latest Git commit hash expected
    with porcelain.open_repo_closing(lister.REPO_PATH) as r:
        expected_last_seen_commit = r.head().decode("ascii")

    assert expected_last_seen_commit is not None
    assert lister.state.last_seen_commit is None

    # First run
    res = lister.run()
    assert res.pages == 1
    assert res.origins == len(expected_origins_0)
    assert expected_last_seen_commit is not None
    assert lister.state.last_seen_commit == expected_last_seen_commit

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    assert len(scheduler_origins) == len(expected_origins_0)

    # Prepare second run, repository state is the same as the one of the first run
    repo_url = prepare_repository_from_archive(archive_path, "General", tmp_path)
    lister = JuliaLister(url=repo_url, scheduler=swh_scheduler)
    assert lister.state.last_seen_commit == expected_last_seen_commit

    # Second run
    res = lister.run()
    assert lister.state.last_seen_commit == expected_last_seen_commit
    assert res.pages == 1
    # Nothing new
    assert res.origins == 0
