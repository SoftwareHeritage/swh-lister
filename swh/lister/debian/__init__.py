# Copyright (C) 2019 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Any, List, Mapping


def debian_init(db_engine,
                override_conf: Mapping[str, Any] = {},
                distributions: List[str] = ['stretch', 'buster'],
                area_names: List[str] = ['main', 'contrib', 'non-free']):
    """Initialize the debian data model.

    Args:
        db_engine: SQLAlchemy manipulation database object
        override_conf: Override conf to pass to instantiate a lister
        distributions: Default distribution to build


    """
    distribution_name = 'Debian'
    from swh.lister.debian.models import Distribution, Area
    from sqlalchemy.orm import sessionmaker
    db_session = sessionmaker(bind=db_engine)()

    existing_distrib = db_session \
        .query(Distribution) \
        .filter(Distribution.name == distribution_name) \
        .one_or_none()
    if not existing_distrib:
        distrib = Distribution(name=distribution_name,
                               type='deb',
                               mirror_uri='http://deb.debian.org/debian/')
        db_session.add(distrib)

        for distribution_name in distributions:
            for area_name in area_names:
                area = Area(
                    name='%s/%s' % (distribution_name, area_name),
                    distribution=distrib,
                )
                db_session.add(area)

        db_session.commit()
    db_session.close()


def register() -> Mapping[str, Any]:
    from .lister import DebianLister
    return {'models': [DebianLister.MODEL],
            'lister': DebianLister,
            'task_modules': ['%s.tasks' % __name__],
            'init': debian_init}
