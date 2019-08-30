# Copyright (C) 2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest

from swh.lister.core.lister_base import ListerBase
from swh.lister.cli import get_lister, SUPPORTED_LISTERS, DEFAULT_BASEURLS

from .test_utils import init_db


def test_get_lister_wrong_input():
    """Unsupported lister should raise"""
    with pytest.raises(ValueError) as e:
        get_lister('unknown', 'db-url')

    assert "Invalid lister" in str(e.value)


def test_get_lister():
    """Instantiating a supported lister should be ok

    """
    db_url = init_db().url()
    supported_listers_with_init = {'npm', 'debian'}
    supported_listers = set(SUPPORTED_LISTERS) - supported_listers_with_init
    for lister_name in supported_listers:
        lst, drop_fn, init_fn, insert_data_fn = get_lister(lister_name, db_url)

        assert isinstance(lst, ListerBase)
        assert drop_fn is None
        assert init_fn is not None
        assert insert_data_fn is None

    for lister_name in supported_listers_with_init:
        lst, drop_fn, init_fn, insert_data_fn = get_lister(lister_name, db_url)

        assert isinstance(lst, ListerBase)
        assert drop_fn is None
        assert init_fn is not None
        assert insert_data_fn is not None

    for lister_name in supported_listers_with_init:
        lst, drop_fn, init_fn, insert_data_fn = get_lister(lister_name, db_url,
                                                           drop_tables=True)

        assert isinstance(lst, ListerBase)
        assert drop_fn is not None
        assert init_fn is not None
        assert insert_data_fn is not None


def test_get_lister_override():
    """Overriding the lister configuration should populate its config

    """
    db_url = init_db().url()

    listers = {
        'gitlab': ('api_baseurl', 'https://gitlab.uni/api/v4/'),
        'phabricator': (
            'api_baseurl',
            'https://somewhere.org/api/diffusion.repository.search'),
    }

    # check the override ends up defined in the lister
    for lister_name, (url_key, url_value) in listers.items():
        lst, drop_fn, init_fn, insert_data_fn = get_lister(
            lister_name, db_url, **{
                'api_baseurl': url_value,
                'priority': 'high',
                'policy': 'oneshot',
            })

        assert getattr(lst, url_key) == url_value
        assert lst.config['priority'] == 'high'
        assert lst.config['policy'] == 'oneshot'

    # check the default urls are used and not the override (since it's not
    # passed)
    for lister_name, (url_key, url_value) in listers.items():
        lst, drop_fn, init_fn, insert_data_fn = get_lister(lister_name, db_url)

        # no override so this does not end up in lister's configuration
        assert url_key not in lst.config

        # then the default base url is used
        default_url = DEFAULT_BASEURLS[lister_name]

        assert getattr(lst, url_key) == default_url
        assert 'priority' not in lst.config
        assert 'oneshot' not in lst.config
