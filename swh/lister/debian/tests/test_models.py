# Copyright (C) 2019 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest

from swh.lister.debian.models import Area, Distribution


def test_area_index_uris_deb(session):
    d = Distribution(
        name="Debian", type="deb", mirror_uri="http://deb.debian.org/debian"
    )
    a = Area(distribution=d, name="unstable/main", active=True,)
    session.add_all([d, a])
    session.commit()

    uris = list(a.index_uris())
    assert uris


def test_area_index_uris_rpm(session):
    d = Distribution(
        name="CentOS", type="rpm", mirror_uri="http://centos.mirrors.proxad.net/"
    )
    a = Area(distribution=d, name="8", active=True,)
    session.add_all([d, a])
    session.commit()

    with pytest.raises(NotImplementedError):
        list(a.index_uris())
