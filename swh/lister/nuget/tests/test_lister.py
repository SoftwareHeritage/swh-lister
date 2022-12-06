# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.lister.nuget.lister import NugetLister

expected_origins = ["https://github.com/sillsdev/libpalaso.git"]
expected_origins_incremental = ["https://github.com/moq/Moq.AutoMocker"]


def test_nuget_lister(datadir, requests_mock_datadir, swh_scheduler):
    lister = NugetLister(scheduler=swh_scheduler)
    res = lister.run()

    assert res.pages == 2
    assert res.origins == 1

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    assert len(scheduler_origins) == len(expected_origins)

    assert [
        (
            scheduled.visit_type,
            scheduled.url,
        )
        for scheduled in sorted(scheduler_origins, key=lambda scheduled: scheduled.url)
    ] == [
        (
            "git",
            url,
        )
        for url in expected_origins
    ]


def test_nuget_lister_incremental(datadir, requests_mock_datadir_visits, swh_scheduler):
    # First run
    lister = NugetLister(scheduler=swh_scheduler)
    assert lister.state.last_listing_date is None

    res = lister.run()
    assert res.pages == 2
    assert res.origins == 1
    assert lister.state.last_listing_date

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    assert [
        (
            scheduled.visit_type,
            scheduled.url,
        )
        for scheduled in sorted(scheduler_origins, key=lambda scheduled: scheduled.url)
    ] == [
        (
            "git",
            url,
        )
        for url in expected_origins
    ]

    last_date = lister.state.last_listing_date

    # Second run
    lister = NugetLister(scheduler=swh_scheduler)
    assert lister.state.last_listing_date == last_date
    res = lister.run()
    # One page and one new origin
    assert lister.state.last_listing_date > last_date
    assert res.pages == 1
    assert res.origins == 1

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    assert [
        (
            scheduled.visit_type,
            scheduled.url,
        )
        for scheduled in sorted(scheduler_origins, key=lambda scheduled: scheduled.url)
    ] == [
        (
            "git",
            url,
        )
        for url in sorted(expected_origins + expected_origins_incremental)
    ]


def test_nuget_lister_incremental_no_changes(
    datadir, requests_mock_datadir, swh_scheduler
):
    # First run
    lister = NugetLister(scheduler=swh_scheduler)
    assert lister.state.last_listing_date is None

    res = lister.run()
    assert res.pages == 2
    assert res.origins == 1
    assert lister.state.last_listing_date

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    assert len(scheduler_origins) == len(expected_origins)

    assert [
        (
            scheduled.visit_type,
            scheduled.url,
        )
        for scheduled in sorted(scheduler_origins, key=lambda scheduled: scheduled.url)
    ] == [
        (
            "git",
            url,
        )
        for url in expected_origins
    ]

    last_date = lister.state.last_listing_date

    # Second run
    lister = NugetLister(scheduler=swh_scheduler)
    assert lister.state.last_listing_date == last_date
    res = lister.run()
    # Nothing new
    assert lister.state.last_listing_date == last_date
    assert res.pages == 0
    assert res.origins == 0
