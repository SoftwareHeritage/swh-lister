# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


def debian_init(db_engine, override_conf=None):
    from swh.storage.schemata.distribution import (
        Distribution, Area)
    from .lister import DebianLister

    lister = DebianLister(override_config=override_conf)

    if not lister.db_session\
                 .query(Distribution)\
                 .filter(Distribution.name == 'Debian')\
                 .one_or_none():

        d = Distribution(
            name='Debian',
            type='deb',
            mirror_uri='http://deb.debian.org/debian/')
        lister.db_session.add(d)

        areas = []
        for distribution_name in ['stretch', 'buster']:
            for area_name in ['main', 'contrib', 'non-free']:
                areas.append(Area(
                    name='%s/%s' % (distribution_name, area_name),
                    distribution=d,
                ))
        lister.db_session.add_all(areas)
        lister.db_session.commit()


def register():
    from .lister import DebianLister
    return {'models': [DebianLister.MODEL],
            'lister': DebianLister,
            'task_modules': ['%s.tasks' % __name__],
            'init': debian_init}
