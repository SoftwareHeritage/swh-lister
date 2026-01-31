# Copyright (C) 2026  The Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest

from swh.lister.gerrit.lister import GerritLister

INSTANCE = "gerrit-review.googlesource.com"
INSTANCE_URL = f"https://{INSTANCE}/"


def test_lister_gerrit_instantiate(swh_scheduler):
    """Building a lister with either an URL or an instance is supported."""
    url = INSTANCE_URL
    api_url = url + "projects/"
    lister = GerritLister(swh_scheduler, url=url)
    assert lister is not None
    assert lister.url == url
    assert lister.api_url == api_url

    assert GerritLister(swh_scheduler, instance=INSTANCE) is not None
    assert lister is not None
    assert lister.url == url
    assert lister.api_url == api_url


def test_lister_gerrit_fail_to_instantiate(swh_scheduler):
    """Building a lister without its URL nor its instance should raise"""
    with pytest.raises(ValueError, match="'url' or 'instance'"):
        GerritLister(swh_scheduler)


def test_lister_gerrit_run(requests_mock_datadir, swh_scheduler):
    """Computing the number of pages scraped during a listing."""
    url = INSTANCE_URL
    lister = GerritLister(swh_scheduler, instance=INSTANCE)

    lister.LIMITs = ("all", 1)

    stats = lister.run()

    origins_count = 4

    assert stats.pages == origins_count
    assert stats.origins == origins_count

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    assert len(scheduler_origins) == origins_count

    for listed_origin in scheduler_origins:
        assert listed_origin.url.startswith(url)
