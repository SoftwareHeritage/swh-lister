# Copyright (C) 2017-2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging

import click

from swh.lister.debian.lister import DebianLister
from swh.lister.debian.models import Area, Distribution, SQLBase


@click.group()
@click.option("--verbose/--no-verbose", default=False)
@click.pass_context
def cli(ctx, verbose):
    ctx.obj["lister"] = DebianLister()
    if verbose:
        loglevel = logging.DEBUG
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
    else:
        loglevel = logging.INFO

    logging.basicConfig(
        format="%(asctime)s %(process)d %(levelname)s %(message)s", level=loglevel,
    )


@cli.command()
@click.pass_context
def create_schema(ctx):
    """Create the schema from the models"""
    SQLBase.metadata.create_all(ctx.obj["lister"].db_engine)


@cli.command()
@click.option("--name", help="The name of the distribution")
@click.option("--type", help="The type of distribution")
@click.option("--mirror-uri", help="The URL to the mirror of the distribution")
@click.option("--area", help="The areas for the distribution", multiple=True)
@click.pass_context
def create_distribution(ctx, name, type, mirror_uri, area):
    to_add = []
    db_session = ctx.obj["lister"].db_session
    d = (
        db_session.query(Distribution)
        .filter(Distribution.name == name)
        .filter(Distribution.type == type)
        .one_or_none()
    )

    if not d:
        d = Distribution(name=name, type=type, mirror_uri=mirror_uri)
        to_add.append(d)

    for area_name in area:
        a = None
        if d.id:
            a = (
                db_session.query(Area)
                .filter(Area.distribution == d)
                .filter(Area.name == area_name)
                .one_or_none()
            )

        if not a:
            a = Area(name=area_name, distribution=d)
            to_add.append(a)

    db_session.add_all(to_add)
    db_session.commit()


@cli.command()
@click.option("--name", help="The name of the distribution")
@click.pass_context
def list_distribution(ctx, name):
    """List the distribution"""
    ctx.obj["lister"].run(name)


if __name__ == "__main__":
    cli(obj={})
