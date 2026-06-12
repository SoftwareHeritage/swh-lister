# Copyright (C) 2026  The Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest

from swh.lister import __version__
from swh.lister.grokmirror.lister import GrokmirrorLister
from swh.lister.pattern import ListerStats

INSTANCE = "git.kernel.org"
INSTANCE_URL = f"https://{INSTANCE}/"


def test_lister_grokmirror_instantiate(swh_scheduler):
    """Building a lister with either an url or an instance is supported."""
    url = INSTANCE_URL
    api_url = url + "manifest.js.gz"
    lister = GrokmirrorLister(swh_scheduler, url=url)
    assert lister is not None
    assert lister.url == url
    assert lister.api_url == api_url

    assert GrokmirrorLister(swh_scheduler, instance=INSTANCE) is not None
    assert lister is not None
    assert lister.url == url
    assert lister.api_url == api_url


def test_lister_grokmirror_fail_to_instantiate(swh_scheduler):
    """Building a lister without its url nor its instance should raise"""
    with pytest.raises(ValueError, match="'url' or 'instance'"):
        GrokmirrorLister(swh_scheduler)


def test_lister_grokmirror_run(requests_mock_datadir, swh_scheduler):
    """Grokmirror lister nominal listing case."""

    url = INSTANCE_URL
    lister = GrokmirrorLister(swh_scheduler, url=url)

    stats = lister.run()

    expected_nb_origins = 7
    assert stats == ListerStats(pages=1, origins=expected_nb_origins)

    # test page parsing
    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    assert len(scheduler_origins) == expected_nb_origins

    # test listed repositories
    for listed_origin in scheduler_origins:
        assert listed_origin.visit_type == "git"
        assert listed_origin.url.startswith(INSTANCE_URL)

    # test user agent content
    for request in requests_mock_datadir.request_history:
        assert "User-Agent" in request.headers
        user_agent = request.headers["User-Agent"]
        assert "Software Heritage grokmirror lister" in user_agent
        assert __version__ in user_agent
