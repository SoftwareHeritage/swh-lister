# Copyright (C) 2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.lister.elm.lister import ElmLister

expected_origins_since_0 = [
    "https://github.com/elm-toulouse/cbor",
    "https://github.com/mercurymedia/elm-ag-grid",
]

expected_origins_since_3 = [
    "https://github.com/miniBill/elm-avataaars",
]


def test_elm_lister(datadir, requests_mock_datadir, swh_scheduler):
    lister = ElmLister(scheduler=swh_scheduler)
    res = lister.run()

    assert res.pages == 1
    # 2 of the 3 entries are related to the same package so the origins count is 2
    assert res.origins == 2

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    assert len(scheduler_origins) == len(expected_origins_since_0)
    assert {
        (
            scheduled.visit_type,
            scheduled.url,
            scheduled.last_update,
        )
        for scheduled in scheduler_origins
    } == {("git", expected, None) for expected in expected_origins_since_0}

    # Check that all_packages_count is set
    assert lister.state.all_packages_count == 3  # 3 entries


def test_elm_lister_incremental(datadir, requests_mock_datadir, swh_scheduler):
    # First run, since=0
    lister = ElmLister(scheduler=swh_scheduler)
    res = lister.run()

    assert res.pages == 1
    # 2 of the 3 entries are related to the same package so the origins count is 2
    assert res.origins == 2

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    assert len(scheduler_origins) == len(expected_origins_since_0)
    assert {
        (
            scheduled.visit_type,
            scheduled.url,
            scheduled.last_update,
        )
        for scheduled in scheduler_origins
    } == {("git", expected, None) for expected in expected_origins_since_0}

    # Check that all_packages_count is set
    assert lister.state.all_packages_count == 3  # 3 entries

    # Second run, since=3
    lister = ElmLister(scheduler=swh_scheduler)
    res = lister.run()
    assert res.pages == 1
    assert res.origins == 1

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    expected_origins = expected_origins_since_0 + expected_origins_since_3
    assert len(scheduler_origins) == len(expected_origins)
    assert {
        (
            scheduled.visit_type,
            scheduled.url,
            scheduled.last_update,
        )
        for scheduled in scheduler_origins
    } == {("git", expected, None) for expected in expected_origins}
    assert lister.state.all_packages_count == 4  # 4 entries

    # Third run, since=4, nothing new
    lister = ElmLister(scheduler=swh_scheduler)
    res = lister.run()
    assert res.pages == 1
    assert res.origins == 0
    assert lister.state.all_packages_count == 4  # 4 entries
