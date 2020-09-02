# Copyright (C) 2019-2020 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest

from swh.lister import __version__


@pytest.fixture
def lister_under_test():
    return "cgit"


def test_lister_no_page(requests_mock_datadir, swh_lister):
    lister = swh_lister

    assert lister.url == "https://git.savannah.gnu.org/cgit/"

    repos = list(lister.get_repos())
    assert len(repos) == 977

    assert repos[0] == "https://git.savannah.gnu.org/cgit/elisp-es.git/"
    # note the url below is NOT a subpath of /cgit/
    assert repos[-1] == "https://git.savannah.gnu.org/path/to/yetris.git/"  # noqa
    # note the url below is NOT on the same server
    assert repos[-2] == "http://example.org/cgit/xstarcastle.git/"


def test_lister_model(requests_mock_datadir, swh_lister):
    lister = swh_lister

    repo = next(lister.get_repos())

    model = lister.build_model(repo)
    assert model == {
        "uid": "https://git.savannah.gnu.org/cgit/elisp-es.git/",
        "name": "elisp-es.git",
        "origin_type": "git",
        "instance": "git.savannah.gnu.org",
        "origin_url": "https://git.savannah.gnu.org/git/elisp-es.git",
    }


def test_lister_with_pages(requests_mock_datadir, swh_lister):
    lister = swh_lister
    lister.url = "https://git.tizen/cgit/"

    repos = list(lister.get_repos())
    # we should have 16 repos (listed on 3 pages)
    assert len(repos) == 16


def test_lister_run(requests_mock_datadir, swh_lister):
    lister = swh_lister
    lister.url = "https://git.tizen/cgit/"
    lister.run()

    r = lister.scheduler.search_tasks(task_type="load-git")
    assert len(r) == 16

    for row in r:
        assert row["type"] == "load-git"
        # arguments check
        args = row["arguments"]["args"]
        assert len(args) == 0

        # kwargs
        kwargs = row["arguments"]["kwargs"]
        assert len(kwargs) == 1
        url = kwargs["url"]
        assert url.startswith("https://git.tizen")

        assert row["policy"] == "recurring"
        assert row["priority"] is None


def test_lister_requests(requests_mock_datadir, swh_lister):
    lister = swh_lister
    lister.url = "https://git.tizen/cgit/"
    lister.run()

    assert len(requests_mock_datadir.request_history) != 0
    for request in requests_mock_datadir.request_history:
        assert "User-Agent" in request.headers
        user_agent = request.headers["User-Agent"]
        assert "Software Heritage Lister" in user_agent
        assert __version__ in user_agent
