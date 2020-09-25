# Copyright (C) 2019 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging

logger = logging.getLogger(__name__)


def test_lister_debian(lister_debian, datadir, requests_mock_datadir):
    """Simple debian listing should create scheduled tasks

    """
    # Run the lister
    lister_debian.run()

    r = lister_debian.scheduler.search_tasks(task_type="load-deb-package")
    assert len(r) == 151

    for row in r:
        assert row["type"] == "load-deb-package"
        # arguments check
        args = row["arguments"]["args"]
        assert len(args) == 0

        # kwargs
        kwargs = row["arguments"]["kwargs"]
        assert set(kwargs.keys()) == {"url", "date", "packages"}

        logger.debug("kwargs: %s", kwargs)
        assert isinstance(kwargs["url"], str)

        assert row["policy"] == "oneshot"
        assert row["priority"] is None
