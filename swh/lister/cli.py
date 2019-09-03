# Copyright (C) 2018-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging
import pkg_resources
from copy import deepcopy

import click
from sqlalchemy import create_engine

from swh.core.cli import CONTEXT_SETTINGS
from swh.lister.core.models import initialize


logger = logging.getLogger(__name__)

LISTERS = {entry_point.name.split('.', 1)[1]: entry_point
           for entry_point in pkg_resources.iter_entry_points('swh.workers')
           if entry_point.name.split('.', 1)[0] == 'lister'}
SUPPORTED_LISTERS = list(LISTERS)


def get_lister(lister_name, db_url=None, **conf):
    """Instantiate a lister given its name.

    Args:
        lister_name (str): Lister's name
        conf (dict): Configuration dict (lister db cnx, policy, priority...)

    Returns:
        Tuple (instantiated lister, drop_tables function, init schema function,
        insert minimum data function)

    """
    if lister_name not in LISTERS:
        raise ValueError(
            'Invalid lister %s: only supported listers are %s' %
            (lister_name, SUPPORTED_LISTERS))
    if db_url:
        conf['lister'] = {'cls': 'local', 'args': {'db': db_url}}
    # To allow api_baseurl override per lister
    registry_entry = LISTERS[lister_name].load()()
    lister_cls = registry_entry['lister']
    lister = lister_cls(override_config=conf)
    return lister


@click.group(name='lister', context_settings=CONTEXT_SETTINGS)
@click.option('--config-file', '-C', default=None,
              type=click.Path(exists=True, dir_okay=False,),
              help="Configuration file.")
@click.option('--db-url', '-d', default=None,
              help='SQLAlchemy DB URL; see '
              '<http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls>')  # noqa
@click.pass_context
def lister(ctx, config_file, db_url):
    '''Software Heritage Lister tools.'''
    from swh.core import config
    ctx.ensure_object(dict)

    override_conf = {}
    if db_url:
        override_conf['lister'] = {
            'cls': 'local',
            'args': {'db': db_url}
        }
    conf = config.read(config_file, override_conf)
    ctx.obj['config'] = conf
    ctx.obj['override_conf'] = override_conf


@lister.command(name='db-init', context_settings=CONTEXT_SETTINGS)
@click.option('--drop-tables', '-D', is_flag=True, default=False,
              help='Drop tables before creating the database schema')
@click.pass_context
def db_init(ctx, drop_tables):
    """Initialize the database model for given listers.

    """

    cfg = ctx.obj['config']
    lister_cfg = cfg['lister']
    if lister_cfg['cls'] != 'local':
        click.echo('A local lister configuration is required')
        ctx.exit(1)

    db_url = lister_cfg['args']['db']
    db_engine = create_engine(db_url)

    for lister, entrypoint in LISTERS.items():
        logger.info('Loading lister %s', lister)
        registry_entry = entrypoint.load()()

    logger.info('Initializing database')
    initialize(db_engine, drop_tables)

    for lister, entrypoint in LISTERS.items():
        init_hook = registry_entry.get('init')
        if callable(init_hook):
            logger.info('Calling init hook for %s', lister)
            init_hook(db_engine)


@lister.command(name='run', context_settings=CONTEXT_SETTINGS,
                help='Trigger a full listing run for a particular forge '
                     'instance. The output of this listing results in '
                     '"oneshot" tasks in the scheduler db with a priority '
                     'defined by the user')
@click.option('--lister', '-l', help='Lister to run',
              type=click.Choice(SUPPORTED_LISTERS))
@click.option('--priority', '-p', default='high',
              type=click.Choice(['high', 'medium', 'low']),
              help='Task priority for the listed repositories to ingest')
@click.argument('options', nargs=-1)
@click.pass_context
def run(ctx, lister, priority, options):
    from swh.scheduler.cli.utils import parse_options

    config = deepcopy(ctx.obj['config'])

    if options:
        config.update(parse_options(options)[1])

    config['priority'] = priority
    config['policy'] = 'oneshot'

    get_lister(lister, **config).run()


if __name__ == '__main__':
    lister()
