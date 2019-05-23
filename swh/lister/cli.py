# Copyright (C) 2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging
import click

from swh.core.cli import CONTEXT_SETTINGS


logger = logging.getLogger(__name__)

SUPPORTED_LISTERS = ['github', 'gitlab', 'bitbucket', 'debian', 'pypi',
                     'npm', 'phabricator']


@click.group(name='lister', context_settings=CONTEXT_SETTINGS)
@click.pass_context
def lister(ctx):
    '''Software Heritage Lister tools.'''
    pass


@lister.command(name='db-init', context_settings=CONTEXT_SETTINGS)
@click.option(
    '--db-url', '-d', default='postgres:///lister-gitlab.com',
    help='SQLAlchemy DB URL; see '
         '<http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls>')  # noqa
@click.argument('listers', required=1, nargs=-1,
                type=click.Choice(SUPPORTED_LISTERS + ['all']))
@click.option('--drop-tables', '-D', is_flag=True, default=False,
              help='Drop tables before creating the database schema')
@click.pass_context
def cli(ctx, db_url, listers, drop_tables):
    """Initialize the database model for given listers.

    """
    override_conf = {
        'lister': {
            'cls': 'local',
            'args': {'db': db_url}
        }
    }

    if 'all' in listers:
        listers = SUPPORTED_LISTERS

    for lister in listers:
        logger.info('Initializing lister %s', lister)
        insert_minimum_data = None
        if lister == 'github':
            from .github.models import IndexingModelBase as ModelBase
            from .github.lister import GitHubLister

            _lister = GitHubLister(
                api_baseurl='https://api.github.com',
                override_config=override_conf)
        elif lister == 'bitbucket':
            from .bitbucket.models import IndexingModelBase as ModelBase
            from .bitbucket.lister import BitBucketLister
            _lister = BitBucketLister(
                api_baseurl='https://api.bitbucket.org/2.0',
                override_config=override_conf)

        elif lister == 'gitlab':
            from .gitlab.models import ModelBase
            from .gitlab.lister import GitLabLister
            _lister = GitLabLister(
                api_baseurl='https://gitlab.com/api/v4/',
                override_config=override_conf)
        elif lister == 'debian':
            from .debian.lister import DebianLister
            ModelBase = DebianLister.MODEL  # noqa
            _lister = DebianLister(override_config=override_conf)

            def insert_minimum_data(lister):
                from swh.storage.schemata.distribution import (
                    Distribution, Area)
                d = Distribution(
                    name='Debian',
                    type='deb',
                    mirror_uri='http://deb.debian.org/debian/')
                lister.db_session.add(d)

                areas = []
                for distribution_name in ['stretch']:
                    for area_name in ['main', 'contrib', 'non-free']:
                        areas.append(Area(
                            name='%s/%s' % (distribution_name, area_name),
                            distribution=d,
                        ))
                lister.db_session.add_all(areas)
                lister.db_session.commit()

        elif lister == 'pypi':
            from .pypi.models import ModelBase
            from .pypi.lister import PyPILister
            _lister = PyPILister(override_config=override_conf)

        elif lister == 'npm':
            from .npm.models import IndexingModelBase as ModelBase
            from .npm.models import NpmVisitModel
            from .npm.lister import NpmLister
            _lister = NpmLister(override_config=override_conf)
            if drop_tables:
                NpmVisitModel.metadata.drop_all(_lister.db_engine)
            NpmVisitModel.metadata.create_all(_lister.db_engine)

        elif lister == 'phabricator':
            from .phabricator.models import IndexingModelBase as ModelBase
            from .phabricator.lister import PhabricatorLister
            _lister = PhabricatorLister(
                forge_url='https://forge.softwareheritage.org',
                api_token='',
                override_config=override_conf)

        else:
            raise ValueError(
                'Invalid lister %s: only supported listers are %s' %
                (lister, SUPPORTED_LISTERS))

        if drop_tables:
            logger.info('Dropping tables for %s', lister)
            ModelBase.metadata.drop_all(_lister.db_engine)

        logger.info('Creating tables for %s', lister)
        ModelBase.metadata.create_all(_lister.db_engine)

        if insert_minimum_data:
            logger.info('Inserting minimal data for %s', lister)
            try:
                insert_minimum_data(_lister)
            except Exception:
                logger.warning(
                    'Failed to insert minimum data in %s', lister)


if __name__ == '__main__':
    cli()
