# Copyright (C) 2019-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest

from swh.lister.cli import SUPPORTED_LISTERS, get_lister

from .test_utils import init_db

lister_args = {
    "phabricator": {
        "instance": "softwareheritage",
        "url": "https://forge.softwareheritage.org/api/diffusion.repository.search",
        "api_token": "bogus",
    },
}


def test_get_lister_wrong_input():
    """Unsupported lister should raise"""
    with pytest.raises(ValueError) as e:
        get_lister("unknown", "db-url")

    assert "Invalid lister" in str(e.value)


def test_get_lister(swh_scheduler_config):
    """Instantiating a supported lister should be ok

    """
    db_url = init_db().url()
    for lister_name in SUPPORTED_LISTERS:
        lst = get_lister(
            lister_name,
            db_url,
            scheduler={"cls": "local", **swh_scheduler_config},
            **lister_args.get(lister_name, {}),
        )
        assert hasattr(lst, "run")
