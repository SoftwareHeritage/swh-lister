# Copyright (C) 2018-2021  The Software Heritage developers
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
from swh.lister import SUPPORTED_LISTERS, get_lister

logger = logging.getLogger(__name__)


@swh_cli_group.group(name="lister", context_settings=CONTEXT_SETTINGS)
@click.option(
    "--config-file",
    "-C",
    default=None,
    type=click.Path(exists=True, dir_okay=False,),
    help="Configuration file.",
)
@click.pass_context
def lister(ctx, config_file):
    """Software Heritage Lister tools."""
    from swh.core import config

    ctx.ensure_object(dict)

    if not config_file:
        config_file = os.environ.get("SWH_CONFIG_FILENAME")
    conf = config.read(config_file)

    ctx.obj["config"] = conf


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
@click.argument("options", nargs=-1)
@click.pass_context
def run(ctx, lister, options):
    from swh.scheduler.cli.utils import parse_options

    config = deepcopy(ctx.obj["config"])

    if options:
        config.update(parse_options(options)[1])

    get_lister(lister, **config).run()


if __name__ == "__main__":
    lister()
