# Copyright (C) 2019 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging
from typing import Any, List, Mapping

logger = logging.getLogger(__name__)


def debian_init(
    db_engine,
    override_conf: Mapping[str, Any] = {},
    distribution_name: str = "Debian",
    suites: List[str] = ["stretch", "buster", "bullseye"],
    components: List[str] = ["main", "contrib", "non-free"],
):
    """Initialize the debian data model.

    Args:
        db_engine: SQLAlchemy manipulation database object
        override_conf: Override conf to pass to instantiate a lister
        distribution_name: Distribution to initialize
        suites: Default suites to register with the lister
        components: Default components to register per suite

    """
    from sqlalchemy.orm import sessionmaker

    from swh.lister.debian.models import Area, Distribution

    db_session = sessionmaker(bind=db_engine)()
    distrib = (
        db_session.query(Distribution)
        .filter(Distribution.name == distribution_name)
        .one_or_none()
    )

    if distrib is None:
        distrib = Distribution(
            name=distribution_name,
            type="deb",
            mirror_uri="http://deb.debian.org/debian/",
        )
        db_session.add(distrib)

    # Check the existing
    existing_area = db_session.query(Area).filter(Area.distribution == distrib).all()
    existing_area = set([a.name for a in existing_area])

    logger.debug("Area already known: %s", ", ".join(existing_area))

    # Create only the new ones
    for suite in suites:
        for component in components:
            area_name = f"{suite}/{component}"
            if area_name in existing_area:
                logger.debug("Area '%s' already set, skipping", area_name)
                continue
            area = Area(name=area_name, distribution=distrib)
            db_session.add(area)

    db_session.commit()
    db_session.close()


def register() -> Mapping[str, Any]:
    from .lister import DebianLister

    return {
        "models": [DebianLister.MODEL],
        "lister": DebianLister,
        "task_modules": ["%s.tasks" % __name__],
        "init": debian_init,
    }
