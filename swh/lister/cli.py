# Copyright (C) 2018-2026  The Software Heritage developers
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

logger = logging.getLogger(__name__)


@swh_cli_group.group(name="lister", context_settings=CONTEXT_SETTINGS)
@click.option(
    "--config-file",
    "-C",
    default=None,
    type=click.Path(
        exists=True,
        dir_okay=False,
    ),
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


@lister.command(name="list", context_settings=CONTEXT_SETTINGS)
@click.pass_context
def list(ctx):
    """List all supported listers"""
    from swh.lister import get_lister_names

    lister_names = "\n".join(sorted(get_lister_names()))
    click.echo(f"Supported listers:\n\n{lister_names}")


@lister.command(name="run", context_settings=CONTEXT_SETTINGS)
@click.option(
    "--lister",
    "-l",
    help="Lister to run",
    required=True,
)
@click.argument("options", nargs=-1)
@click.pass_context
def run(ctx, lister, options):
    """Trigger a full listing run for a particular forge instance

    To get the list of supported listers, use the following command:

        $ swh lister list
    """
    from swh.lister import get_lister
    from swh.scheduler.cli.utils import parse_options

    config = deepcopy(ctx.obj["config"])

    if options:
        config.update(parse_options(options)[1])

    if "scheduler" not in config:
        logger.warning(
            "No scheduler configuration detected, using a temporary instance "
            "with a memory backend instead."
        )

        config["scheduler"] = {"cls": "memory"}

    print(get_lister(lister, **config).run())


if __name__ == "__main__":
    lister()
