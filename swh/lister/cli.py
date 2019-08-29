# Copyright (C) 2018-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging
import click

from swh.core.cli import CONTEXT_SETTINGS


logger = logging.getLogger(__name__)

SUPPORTED_LISTERS = ['github', 'gitlab', 'bitbucket', 'debian', 'pypi',
                     'npm', 'phabricator', 'gnu', 'cran', 'cgit', 'packagist']


# Base urls for most listers
DEFAULT_BASEURLS = {
    'gitlab': 'https://gitlab.com/api/v4/',
    'phabricator': 'https://forge.softwareheritage.org',
    'cgit': (
        'http://git.savannah.gnu.org/cgit/',
        'http://git.savannah.gnu.org/git/'
    ),
}


def get_lister(lister_name, db_url, drop_tables=False, **conf):
    """Instantiate a lister given its name.

    Args:
        lister_name (str): Lister's name
        db_url (str): Db's service url access
        conf (dict): Extra configuration (policy, priority for example)

    Returns:
        Tuple (instantiated lister, drop_tables function, init schema function,
        insert minimum data function)

    """
    override_conf = {
        'lister': {
            'cls': 'local',
            'args': {'db': db_url}
        },
        **conf,
    }

    # To allow api_baseurl override per lister
    if 'api_baseurl' in override_conf:
        api_baseurl = override_conf.pop('api_baseurl')
    else:
        api_baseurl = DEFAULT_BASEURLS.get(lister_name)

    insert_minimum_data_fn = None
    if lister_name == 'github':
        from .github.models import IndexingModelBase as ModelBase
        from .github.lister import GitHubLister

        _lister = GitHubLister(api_baseurl='https://api.github.com',
                               override_config=override_conf)
    elif lister_name == 'bitbucket':
        from .bitbucket.models import IndexingModelBase as ModelBase
        from .bitbucket.lister import BitBucketLister
        _lister = BitBucketLister(api_baseurl='https://api.bitbucket.org/2.0',
                                  override_config=override_conf)

    elif lister_name == 'gitlab':
        from .gitlab.models import ModelBase
        from .gitlab.lister import GitLabLister
        _lister = GitLabLister(api_baseurl=api_baseurl,
                               override_config=override_conf)
    elif lister_name == 'debian':
        from .debian.lister import DebianLister
        ModelBase = DebianLister.MODEL  # noqa
        _lister = DebianLister(override_config=override_conf)

        def insert_minimum_data_fn(lister_name, lister):
            logger.info('Inserting minimal data for %s', lister_name)
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

    elif lister_name == 'pypi':
        from .pypi.models import ModelBase
        from .pypi.lister import PyPILister
        _lister = PyPILister(override_config=override_conf)

    elif lister_name == 'npm':
        from .npm.models import IndexingModelBase as ModelBase
        from .npm.models import NpmVisitModel
        from .npm.lister import NpmLister
        _lister = NpmLister(override_config=override_conf)

        def insert_minimum_data_fn(lister_name, lister):
            logger.info('Inserting minimal data for %s', lister_name)
            if drop_tables:
                NpmVisitModel.metadata.drop_all(lister.db_engine)
                NpmVisitModel.metadata.create_all(lister.db_engine)

    elif lister_name == 'phabricator':
        from .phabricator.models import IndexingModelBase as ModelBase
        from .phabricator.lister import PhabricatorLister
        _lister = PhabricatorLister(forge_url=api_baseurl,
                                    override_config=override_conf)

    elif lister_name == 'gnu':
        from .gnu.models import ModelBase
        from .gnu.lister import GNULister
        _lister = GNULister(override_config=override_conf)

    elif lister_name == 'cran':
        from .cran.models import ModelBase
        from .cran.lister import CRANLister
        _lister = CRANLister(override_config=override_conf)

    elif lister_name == 'cgit':
        from .cgit.models import ModelBase
        from .cgit.lister import CGitLister
        if isinstance(api_baseurl, str):
            _lister = CGitLister(url=api_baseurl,
                                 override_config=override_conf)
        else:  # tuple
            _lister = CGitLister(url=api_baseurl[0],
                                 url_prefix=api_baseurl[1],
                                 override_config=override_conf)

    elif lister_name == 'packagist':
        from .packagist.models import ModelBase  # noqa
        from .packagist.lister import PackagistLister
        _lister = PackagistLister(override_config=override_conf)

    else:
        raise ValueError(
            'Invalid lister %s: only supported listers are %s' %
            (lister_name, SUPPORTED_LISTERS))

    drop_table_fn = None
    if drop_tables:
        def drop_table_fn(lister_name, lister):
            logger.info('Dropping tables for %s', lister_name)
            ModelBase.metadata.drop_all(lister.db_engine)

    def init_schema_fn(lister_name, lister):
        logger.info('Creating tables for %s', lister_name)
        ModelBase.metadata.create_all(lister.db_engine)

    return _lister, drop_table_fn, init_schema_fn, insert_minimum_data_fn


@click.group(name='lister', context_settings=CONTEXT_SETTINGS)
@click.pass_context
def lister(ctx):
    '''Software Heritage Lister tools.'''
    pass


@lister.command(name='db-init', context_settings=CONTEXT_SETTINGS)
@click.option('--db-url', '-d', default='postgres:///lister',
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
    if 'all' in listers:
        listers = SUPPORTED_LISTERS

    for lister_name in listers:
        logger.info('Initializing lister %s', lister_name)
        lister, drop_schema_fn, init_schema_fn, insert_minimum_data_fn = \
            get_lister(lister_name, db_url, drop_tables=drop_tables)

        if drop_schema_fn:
            drop_schema_fn(lister_name, lister)

        init_schema_fn(lister_name, lister)

        if insert_minimum_data_fn:
            insert_minimum_data_fn(lister_name, lister)


@lister.command(name='run', context_settings=CONTEXT_SETTINGS,
                help='Trigger a full listing run for a particular forge '
                     'instance. The output of this listing results in '
                     '"oneshot" tasks in the scheduler db with a priority '
                     'defined by the user')
@click.option('--db-url', '-d', default='postgres:///lister',
              help='SQLAlchemy DB URL; see '
                   '<http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls>')  # noqa
@click.option('--lister', '-l', help='Lister to run',
              type=click.Choice(SUPPORTED_LISTERS))
@click.option('--priority', '-p', default='high',
              type=click.Choice(['high', 'medium', 'low']),
              help='Task priority for the listed repositories to ingest')
@click.argument('options', nargs=-1)
@click.pass_context
def run(ctx, db_url, lister, priority, options):
    from swh.scheduler.cli.utils import parse_options

    if options:
        _, kwargs = parse_options(options)
    else:
        kwargs = {}

    override_config = {
        'priority': priority,
        'policy': 'oneshot',
        **kwargs,
    }

    lister, _, _, _ = get_lister(lister, db_url, **override_config)
    lister.run()


if __name__ == '__main__':
    cli()
