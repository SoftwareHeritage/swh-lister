# Copyright (C) 2018-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os
import logging
import pkg_resources
from copy import deepcopy
from importlib import import_module

import click
from sqlalchemy import create_engine

from swh.core.cli import CONTEXT_SETTINGS
from swh.scheduler import get_scheduler
from swh.scheduler.task import SWHTask
from swh.lister.core.models import initialize


logger = logging.getLogger(__name__)

LISTERS = {entry_point.name.split('.', 1)[1]: entry_point
           for entry_point in pkg_resources.iter_entry_points('swh.workers')
           if entry_point.name.split('.', 1)[0] == 'lister'}
SUPPORTED_LISTERS = list(LISTERS)

# the key in this dict is the suffix used to match new task-type to be added.
# For example for a task which function name is "list_gitlab_full', the default
# value used when inserting a new task-type in the scheduler db will be the one
# under the 'full' key below (because it matches xxx_full).
DEFAULT_TASK_TYPE = {
    'full': {  # for tasks like 'list_xxx_full()'
      'default_interval': '90 days',
      'min_interval': '90 days',
      'max_interval': '90 days',
      'backoff_factor': 1
      },
    '*': {  # value if not suffix matches
      'default_interval': '1 day',
      'min_interval': '1 day',
      'max_interval': '1 day',
      'backoff_factor': 1
      },
    }


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
    if not config_file:
        config_file = os.environ.get('SWH_CONFIG_FILENAME')
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

    registry = {}
    for lister, entrypoint in LISTERS.items():
        logger.info('Loading lister %s', lister)
        registry[lister] = entrypoint.load()()

    logger.info('Initializing database')
    initialize(db_engine, drop_tables)

    for lister, entrypoint in LISTERS.items():
        registry_entry = registry[lister]
        init_hook = registry_entry.get('init')
        if callable(init_hook):
            logger.info('Calling init hook for %s', lister)
            init_hook(db_engine)


@lister.command(name='register-task-types', context_settings=CONTEXT_SETTINGS)
@click.option('--lister', '-l', 'listers', multiple=True,
              default=('all', ), show_default=True,
              help='Only registers task-types for these listers',
              type=click.Choice(['all'] + SUPPORTED_LISTERS))
@click.pass_context
def register_task_types(ctx, listers):
    """Insert missing task-type entries in the scheduler

    According to declared tasks in each loaded lister plugin.
    """

    cfg = ctx.obj['config']
    scheduler = get_scheduler(**cfg['scheduler'])

    for lister, entrypoint in LISTERS.items():
        if 'all' not in listers and lister not in listers:
            continue
        logger.info('Loading lister %s', lister)

        registry_entry = entrypoint.load()()
        for task_module in registry_entry['task_modules']:
            mod = import_module(task_module)
            for task_name in (x for x in dir(mod) if not x.startswith('_')):
                taskobj = getattr(mod, task_name)
                if isinstance(taskobj, SWHTask):
                    task_type = task_name.replace('_', '-')
                    task_cfg = registry_entry.get('task_types', {}).get(
                        task_type, {})
                    ensure_task_type(task_type, taskobj, task_cfg, scheduler)


def ensure_task_type(task_type, swhtask, task_config, scheduler):
    """Ensure a task-type is known by the scheduler

    Args:
        task_type (str): the type of the task to check/insert (correspond to
            the 'type' field in the db)
        swhtask (SWHTask): the SWHTask instance the task-type correspond to
        task_config (dict): a dict with specific/overloaded values for the
            task-type to be created
        scheduler: the scheduler object used to access the scheduler db
    """
    for suffix, defaults in DEFAULT_TASK_TYPE.items():
        if task_type.endswith('-' + suffix):
            task_type_dict = defaults.copy()
            break
    else:
        task_type_dict = DEFAULT_TASK_TYPE['*'].copy()

    task_type_dict['type'] = task_type
    task_type_dict['backend_name'] = swhtask.name
    if swhtask.__doc__:
        task_type_dict['description'] = swhtask.__doc__.splitlines()[0]

    task_type_dict.update(task_config)

    current_task_type = scheduler.get_task_type(task_type)
    if current_task_type:
        # check some stuff
        if current_task_type['backend_name'] != task_type_dict['backend_name']:
            logger.warning('Existing task type %s for lister %s has a '
                           'different backend name than current '
                           'code version provides (%s vs. %s)',
                           task_type,
                           lister,
                           current_task_type['backend_name'],
                           task_type_dict['backend_name'],
                           )
    else:
        logger.info('Create task type %s in scheduler', task_type)
        logger.debug('  %s', task_type_dict)
        scheduler.create_task_type(task_type_dict)


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
