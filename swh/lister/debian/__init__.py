# Copyright (C) 2019 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Any, List, Mapping


def debian_init(db_engine, lister=None,
                override_conf: Mapping[str, Any] = {},
                distributions: List[str] = ['stretch', 'buster'],
                area_names: List[str] = ['main', 'contrib', 'non-free']):
    """Initialize the debian data model.

    Args:
        db_engine: SQLAlchemy manipulation database object
        lister: Debian lister instance. None by default.
        override_conf: Override conf to pass to instantiate a lister
        distributions: Default distribution to build


    """
    distribution_name = 'Debian'
    from swh.storage.schemata.distribution import (
        Distribution, Area)

    if lister is None:
        from .lister import DebianLister
        lister = DebianLister(distribution=distribution_name,
                              override_config=override_conf)

    if not lister.db_session\
                 .query(Distribution)\
                 .filter(Distribution.name == distribution_name)\
                 .one_or_none():

        d = Distribution(
            name=distribution_name,
            type='deb',
            mirror_uri='http://deb.debian.org/debian/')
        lister.db_session.add(d)

        areas = []
        for distribution_name in distributions:
            for area_name in area_names:
                areas.append(Area(
                    name='%s/%s' % (distribution_name, area_name),
                    distribution=d,
                ))
        lister.db_session.add_all(areas)
        lister.db_session.commit()


def register() -> Mapping[str, Any]:
    from .lister import DebianLister
    return {'models': [DebianLister.MODEL],
            'lister': DebianLister,
            'task_modules': ['%s.tasks' % __name__],
            'init': debian_init}
