import json
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote

import pytest
from requests import HTTPError

from swh.lister.hex.lister import HexLister, ListedOrigin
from swh.scheduler.interface import SchedulerInterface


@pytest.fixture
def hexpm_page(datadir):
    def get_page(page_id: int):
        text = Path(datadir, "https_hex.pm", f"page{page_id}.json").read_text()
        page_result = json.loads(text)
        origins = [origin["html_url"] for origin in page_result]
        return origins, page_result

    return get_page


def check_listed_origins(lister_urls: List[str], scheduler_origins: List[ListedOrigin]):
    """Asserts that the two collections have the same origin URLs."""
    assert set(lister_urls) == {origin.url for origin in scheduler_origins}


@pytest.fixture
def mock_hexpm_page(requests_mock):
    def func(
        updated_after: str,
        body: Optional[List[dict]],
        status_code: int = 200,
    ):
        search_query = quote(f"updated_after:{updated_after}")
        page_url = f"https://hex.pm/api/packages/?search={search_query}"
        requests_mock.get(
            page_url, json=body, complete_qs=True, status_code=status_code
        )

    return func


def test_full_lister_hex(
    swh_scheduler: SchedulerInterface,
    hexpm_page,
    mock_hexpm_page,
):
    """
    Simulate a full listing of packages for hex (erlang package manager)
    """
    p1_origin_urls, p1_json = hexpm_page(1)
    p2_origin_urls, p2_json = hexpm_page(2)
    p3_origin_urls, p3_json = hexpm_page(3)

    mock_hexpm_page("0001-01-01T00:00:00.000000Z", p1_json)
    mock_hexpm_page("2018-01-30T04:56:03.053561Z", p2_json)
    mock_hexpm_page("2019-03-27T00:32:47.822901Z", p3_json)
    mock_hexpm_page("2022-09-09T21:00:14.993273Z", [])

    lister = HexLister(swh_scheduler, page_size=4)

    stats = lister.run()
    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    lister_state = lister.get_state_from_scheduler()

    assert stats.pages == 3  # 4 + 4 + 2 (2 < page_size so lister stops at page 3)
    assert stats.origins == 10

    check_listed_origins(
        p1_origin_urls + p2_origin_urls + p3_origin_urls, scheduler_origins
    )

    assert lister_state.page_updated_at == "2022-09-09T21:00:14.993273Z"
    assert lister.updated


def test_hex_incremental_lister(
    swh_scheduler,
    mock_hexpm_page,
    hexpm_page,
):
    lister = HexLister(swh_scheduler, page_size=4)

    # First run: P1 and P2 return 4 origins each and P3 returns 0
    p1_origin_urls, p1_json = hexpm_page(1)
    p2_origin_urls, p2_json = hexpm_page(2)

    mock_hexpm_page("0001-01-01T00:00:00.000000Z", p1_json)
    mock_hexpm_page("2018-01-30T04:56:03.053561Z", p2_json)
    mock_hexpm_page("2019-03-27T00:32:47.822901Z", [])

    stats = lister.run()

    assert stats.pages == 3
    assert stats.origins == 8

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    lister_state = lister.get_state_from_scheduler()
    assert lister_state.page_updated_at == "2019-03-27T00:32:47.822901Z"
    assert lister.updated

    check_listed_origins(p1_origin_urls + p2_origin_urls, scheduler_origins)

    lister.updated = False  # Reset the flag

    # Second run: P3 isn't empty anymore
    p3_origin_urls, p3_json = hexpm_page(3)

    mock_hexpm_page("2019-03-27T00:32:47.822901Z", p3_json)
    mock_hexpm_page("2022-09-09T21:00:14.993273Z", [])

    stats = lister.run()

    assert stats.pages == 1
    assert stats.origins == 2

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    lister_state = lister.get_state_from_scheduler()
    assert lister.state.page_updated_at == "2022-09-09T21:00:14.993273Z"
    assert lister.updated

    check_listed_origins(
        p1_origin_urls + p2_origin_urls + p3_origin_urls, scheduler_origins
    )

    lister.updated = False  # Reset the flag

    # Third run: No new origins
    # The lister should revisit the last page (P4)

    stats = lister.run()

    assert stats.pages == 1
    assert stats.origins == 0

    lister_state = lister.get_state_from_scheduler()
    assert lister_state.page_updated_at == "2022-09-09T21:00:14.993273Z"
    assert lister.updated is False  # No new origins so state isn't updated

    check_listed_origins(
        p1_origin_urls + p2_origin_urls + p3_origin_urls, scheduler_origins
    )


@pytest.mark.parametrize("http_code", [400, 500])
def test_hex_lister_http_error(swh_scheduler, http_code, mock_hexpm_page, hexpm_page):
    """Test handling of some HTTP errors commonly encountered"""
    lister = HexLister(swh_scheduler, page_size=4)

    p1_origin_urls, p1_json = hexpm_page(1)
    _, p3_json = hexpm_page(3)

    mock_hexpm_page("0001-01-01T00:00:00.000000Z", p1_json)
    mock_hexpm_page("2018-01-30T04:56:03.053561Z", None, http_code)
    mock_hexpm_page("2019-03-27T00:32:47.822901Z", p3_json)

    with pytest.raises(HTTPError):
        lister.run()

    # Only P1 should be listed
    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    check_listed_origins(p1_origin_urls, scheduler_origins)
