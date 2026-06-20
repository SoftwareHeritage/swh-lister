# Copyright (C) 2026  The Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest

from swh.lister import __version__
from swh.lister.hgweb.lister import HgwebLister
from swh.lister.pattern import ListerStats

INSTANCE = "repo.mercurial-scm.org"
INSTANCE_URL = f"https://{INSTANCE}/"


def test_lister_hgweb_instantiate(swh_scheduler):
    """Build a lister with either an url or an instance is supported."""
    url = INSTANCE_URL
    lister = HgwebLister(swh_scheduler, url=url)
    assert lister is not None
    assert lister.url == url

    assert HgwebLister(swh_scheduler, instance=INSTANCE) is not None
    assert lister is not None
    assert lister.url == url


def test_lister_hgweb_fail_to_instantiate(swh_scheduler):
    """Build a lister without its url nor its instance should raise"""
    # ... It will raise without any of those
    with pytest.raises(ValueError, match="'url' or 'instance'"):
        HgwebLister(swh_scheduler)


@pytest.mark.parametrize(
    "url,instance,expected_pages,expected_nb_origins",
    [
        (INSTANCE_URL, INSTANCE, 1, 6),
        ("https://hg.ztfy.org/", "hg.ztfy.org", 4, 40),
        ("https://hg-edge.mozilla.org/", "hg-edge.mozilla.org", 9, 144),
    ],
)
@pytest.mark.parametrize("enable_api", [True, False])
def test_lister_hgweb_run(
    url,
    instance,
    enable_api,
    expected_pages,
    expected_nb_origins,
    requests_mock,
    datadir,
    requests_mock_datadir,
    swh_scheduler,
):
    """Hgweb lister nominal listing case."""

    lister = HgwebLister(swh_scheduler, url=url, enable_api=enable_api)

    stats = lister.run()

    assert stats == ListerStats(
        pages=expected_pages,
        origins=expected_nb_origins,
    )

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    assert len(scheduler_origins) == expected_nb_origins

    assert url.startswith("https://")

    # test listed repositories
    for listed_origin in scheduler_origins:
        assert listed_origin.visit_type == "hg"
        assert listed_origin.url.startswith(url)
        assert listed_origin.url.startswith("https://")
        assert listed_origin.last_update is not None

    # test user agent content
    for request in requests_mock_datadir.request_history:
        assert "User-Agent" in request.headers
        user_agent = request.headers["User-Agent"]
        assert "Software Heritage hgweb lister" in user_agent
        assert __version__ in user_agent
