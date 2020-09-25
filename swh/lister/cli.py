# Copyright (C) 2018-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from copy import deepcopy
import logging

# WARNING: do not import unnecessary things here to keep cli startup time under
# control
import os

import click

from swh.core.cli import CONTEXT_SETTINGS
from swh.core.cli import swh as swh_cli_group
from swh.lister import LISTERS, SUPPORTED_LISTERS, get_lister

logger = logging.getLogger(__name__)


# the key in this dict is the suffix used to match new task-type to be added.
# For example for a task which function name is "list_gitlab_full', the default
# value used when inserting a new task-type in the scheduler db will be the one
# under the 'full' key below (because it matches xxx_full).
DEFAULT_TASK_TYPE = {
    "full": {  # for tasks like 'list_xxx_full()'
        "default_interval": "90 days",
        "min_interval": "90 days",
        "max_interval": "90 days",
        "backoff_factor": 1,
    },
    "*": {  # value if not suffix matches
        "default_interval": "1 day",
        "min_interval": "1 day",
        "max_interval": "1 day",
        "backoff_factor": 1,
    },
}


@swh_cli_group.group(name="lister", context_settings=CONTEXT_SETTINGS)
@click.option(
    "--config-file",
    "-C",
    default=None,
    type=click.Path(exists=True, dir_okay=False,),
    help="Configuration file.",
)
@click.option(
    "--db-url",
    "-d",
    default=None,
    help="SQLAlchemy DB URL; see "
    "<http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls>",
)  # noqa
@click.pass_context
def lister(ctx, config_file, db_url):
    """Software Heritage Lister tools."""
    from swh.core import config

    ctx.ensure_object(dict)

    if not config_file:
        config_file = os.environ.get("SWH_CONFIG_FILENAME")
    conf = config.read(config_file)
    if db_url:
        conf["lister"] = {"cls": "local", "args": {"db": db_url}}
    ctx.obj["config"] = conf


@lister.command(name="db-init", context_settings=CONTEXT_SETTINGS)
@click.option(
    "--drop-tables",
    "-D",
    is_flag=True,
    default=False,
    help="Drop tables before creating the database schema",
)
@click.pass_context
def db_init(ctx, drop_tables):
    """Initialize the database model for given listers.

    """
    from sqlalchemy import create_engine

    from swh.lister.core.models import initialize

    cfg = ctx.obj["config"]
    lister_cfg = cfg["lister"]
    if lister_cfg["cls"] != "local":
        click.echo("A local lister configuration is required")
        ctx.exit(1)

    db_url = lister_cfg["args"]["db"]
    db_engine = create_engine(db_url)

    registry = {}
    for lister, entrypoint in LISTERS.items():
        logger.info("Loading lister %s", lister)
        registry[lister] = entrypoint.load()()

    logger.info("Initializing database")
    initialize(db_engine, drop_tables)

    for lister, entrypoint in LISTERS.items():
        registry_entry = registry[lister]
        init_hook = registry_entry.get("init")
        if callable(init_hook):
            logger.info("Calling init hook for %s", lister)
            init_hook(db_engine)


@lister.command(
    name="run",
    context_settings=CONTEXT_SETTINGS,
    help="Trigger a full listing run for a particular forge "
    "instance. The output of this listing results in "
    '"oneshot" tasks in the scheduler db with a priority '
    "defined by the user",
)
@click.option(
    "--lister", "-l", help="Lister to run", type=click.Choice(SUPPORTED_LISTERS)
)
@click.option(
    "--priority",
    "-p",
    default="high",
    type=click.Choice(["high", "medium", "low"]),
    help="Task priority for the listed repositories to ingest",
)
@click.argument("options", nargs=-1)
@click.pass_context
def run(ctx, lister, priority, options):
    from swh.scheduler.cli.utils import parse_options

    config = deepcopy(ctx.obj["config"])

    if options:
        config.update(parse_options(options)[1])

    config["priority"] = priority
    config["policy"] = "oneshot"

    get_lister(lister, **config).run()


if __name__ == "__main__":
    lister()
