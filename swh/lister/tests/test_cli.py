# Copyright (C) 2019-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest

from swh.lister.cli import SUPPORTED_LISTERS, get_lister
from swh.lister.core.lister_base import ListerBase

from .test_utils import init_db


def test_get_lister_wrong_input():
    """Unsupported lister should raise"""
    with pytest.raises(ValueError) as e:
        get_lister("unknown", "db-url")

    assert "Invalid lister" in str(e.value)


def test_get_lister():
    """Instantiating a supported lister should be ok

    """
    db_url = init_db().url()
    # exclude listers because they need special instantiation treatment unrelated to
    # this test (launchpad: network mock, gnu: scheduler load task)
    listers_to_instantiate = set(SUPPORTED_LISTERS) - {"launchpad", "gnu"}
    for lister_name in listers_to_instantiate:
        lst = get_lister(lister_name, db_url)
        assert isinstance(lst, ListerBase)


def test_get_lister_override():
    """Overriding the lister configuration should populate its config

    """
    db_url = init_db().url()

    listers = {
        "gitlab": "https://other.gitlab.uni/api/v4/",
        "phabricator": "https://somewhere.org/api/diffusion.repository.search",
        "cgit": "https://some.where/cgit",
    }

    # check the override ends up defined in the lister
    for lister_name, url in listers.items():
        lst = get_lister(
            lister_name,
            db_url,
            **{"url": url, "priority": "high", "policy": "oneshot",},
        )

        assert lst.url == url
        assert lst.config["priority"] == "high"
        assert lst.config["policy"] == "oneshot"

    # check the default urls are used and not the override (since it's not
    # passed)
    for lister_name, url in listers.items():
        lst = get_lister(lister_name, db_url)

        # no override so this does not end up in lister's configuration
        assert "url" not in lst.config
        assert "priority" not in lst.config
        assert "oneshot" not in lst.config
        assert lst.url == lst.DEFAULT_URL
