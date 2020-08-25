# Copyright (C) 2019 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


def test_pypi_lister(lister_pypi, requests_mock_datadir):
    lister_pypi.run()

    r = lister_pypi.scheduler.search_tasks(task_type="load-pypi")
    assert len(r) == 4

    for row in r:
        assert row["type"] == "load-pypi"
        # arguments check
        args = row["arguments"]["args"]
        assert len(args) == 0

        # kwargs
        kwargs = row["arguments"]["kwargs"]
        assert len(kwargs) == 1

        origin_url = kwargs["url"]
        assert "https://pypi.org/project" in origin_url

        assert row["policy"] == "recurring"
        assert row["priority"] is None
