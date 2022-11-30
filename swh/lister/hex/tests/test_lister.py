import json
from pathlib import Path
from typing import List

import pytest

from swh.lister.hex.lister import HexLister, ListedOrigin
from swh.scheduler.interface import SchedulerInterface


@pytest.fixture
def hexpm_page(datadir):
    def get_page(page_id: int):
        # FIXME: Update the test data to match ?sort=name
        text = Path(datadir, "https_hex.pm", f"page{page_id}.json").read_text()
        page_result = json.loads(text)
        origins = [origin["html_url"] for origin in page_result]
        return origins, page_result

    return get_page


def check_listed_origins(lister_urls: List[str], scheduler_origins: List[ListedOrigin]):
    """Asserts that the two collections have the same origin URLs."""
    assert set(lister_urls) == {origin.url for origin in scheduler_origins}


def test_full_lister_hex(
    swh_scheduler: SchedulerInterface,
    requests_mock,
    hexpm_page,
):
    """
    Simulate a full listing of packages for hex (erlang package manager)
    """
    p1_origin_urls, p1_json = hexpm_page(1)
    p2_origin_urls, p2_json = hexpm_page(2)
    p3_origin_urls, p3_json = hexpm_page(3)

    requests_mock.get("https://hex.pm/api/packages/?page=1", json=p1_json)
    requests_mock.get("https://hex.pm/api/packages/?page=2", json=p2_json)
    requests_mock.get("https://hex.pm/api/packages/?page=3", json=p3_json)
    requests_mock.get("https://hex.pm/api/packages/?page=4", json=[])

    lister = HexLister(swh_scheduler)

    stats = lister.run()
    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    lister_state = lister.get_state_from_scheduler()

    assert stats.pages == 4
    assert stats.origins == 10  # 4 + 4 + 2 + 0

    check_listed_origins(
        p1_origin_urls + p2_origin_urls + p3_origin_urls, scheduler_origins
    )

    assert lister_state.last_page_id == 4
    assert lister_state.last_pkg_name == "logger_dev"
    assert lister.updated


def test_gogs_incremental_lister(
    swh_scheduler,
    requests_mock,
    hexpm_page,
):
    lister = HexLister(swh_scheduler)

    # First run: P1 and P2 return 4 origins each and P3 returns 0
    p1_origin_urls, p1_json = hexpm_page(1)
    p2_origin_urls, p2_json = hexpm_page(2)

    requests_mock.get("https://hex.pm/api/packages/?page=1", json=p1_json)
    requests_mock.get("https://hex.pm/api/packages/?page=2", json=p2_json)
    requests_mock.get("https://hex.pm/api/packages/?page=3", json=[])

    stats = lister.run()

    assert stats.pages == 3
    assert stats.origins == 8

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    lister_state = lister.get_state_from_scheduler()
    assert lister_state.last_page_id == 3
    assert lister.state.last_pkg_name == "alchemy_vm"
    assert lister.updated

    check_listed_origins(p1_origin_urls + p2_origin_urls, scheduler_origins)

    lister.updated = False  # Reset the flag

    # Second run: P3 isn't empty anymore
    p3_origin_urls, p3_json = hexpm_page(3)

    requests_mock.get("https://hex.pm/api/packages/?page=3", json=p3_json)
    requests_mock.get(
        "https://hex.pm/api/packages/?page=4", json=[]
    )  # TODO: Try with 40x/50x here?

    stats = lister.run()

    assert stats.pages == 2
    assert stats.origins == 2

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    lister_state = lister.get_state_from_scheduler()
    assert (
        lister_state.last_page_id == 4
    )  # TODO: Shouldn't this be 3 given that P4 is empty?
    assert lister.state.last_pkg_name == "logger_dev"
    assert lister.updated

    check_listed_origins(
        p1_origin_urls + p2_origin_urls + p3_origin_urls, scheduler_origins
    )

    lister.updated = False  # Reset the flag

    # Third run: No new origins
    # The lister should revisit the last page (P3)

    stats = lister.run()

    assert stats.pages == 1
    assert (
        stats.origins == 0
    )  # FIXME: inconsistent with Gogs lister. Either of them could be wrong

    lister_state = lister.get_state_from_scheduler()
    assert (
        lister_state.last_page_id == 4
    )  # TODO: Shouldn't this be 3 given that P4 is empty?
    assert lister.state.last_pkg_name == "logger_dev"
    assert lister.updated is False  # No new origins so state isn't updated

    check_listed_origins(
        p1_origin_urls + p2_origin_urls + p3_origin_urls, scheduler_origins
    )
