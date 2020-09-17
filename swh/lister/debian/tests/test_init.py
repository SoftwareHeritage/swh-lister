# Copyright (C) 2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest

from swh.lister.debian import debian_init
from swh.lister.debian.models import Area, Distribution


@pytest.fixture
def engine(session):
    session.autoflush = False
    return session.bind


def test_debian_init_step(engine, session):
    distribution_name = "KaliLinux"

    distrib = (
        session.query(Distribution)
        .filter(Distribution.name == distribution_name)
        .one_or_none()
    )
    assert distrib is None

    all_area = session.query(Area).all()
    assert all_area == []

    suites = ["wheezy", "jessie"]
    components = ["main", "contrib"]

    debian_init(
        engine,
        distribution_name=distribution_name,
        suites=suites,
        components=components,
    )
    distrib = (
        session.query(Distribution)
        .filter(Distribution.name == distribution_name)
        .one_or_none()
    )

    assert distrib is not None
    assert distrib.name == distribution_name
    assert distrib.type == "deb"
    assert distrib.mirror_uri == "http://deb.debian.org/debian/"

    all_area = session.query(Area).all()
    assert len(all_area) == 2 * 2, "2 suites * 2 components per suite"

    expected_area_names = []
    for suite in suites:
        for component in components:
            expected_area_names.append(f"{suite}/{component}")

    for area in all_area:
        area.id = None
        assert area.distribution == distrib
        assert area.name in expected_area_names

    # check idempotency (on exact same call)

    debian_init(
        engine,
        distribution_name=distribution_name,
        suites=suites,
        components=components,
    )

    distribs = (
        session.query(Distribution).filter(Distribution.name == distribution_name).all()
    )

    assert len(distribs) == 1
    distrib = distribs[0]

    all_area = session.query(Area).all()
    assert len(all_area) == 2 * 2, "2 suites * 2 components per suite"

    # Add a new suite
    debian_init(
        engine,
        distribution_name=distribution_name,
        suites=["lenny"],
        components=components,
    )

    all_area = [a.name for a in session.query(Area).all()]
    assert len(all_area) == (2 + 1) * 2, "3 suites * 2 components per suite"
