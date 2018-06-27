# Copyright (C) 2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import click


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option(
    '--db-url', '-d', default='postgres:///lister-gitlab.com',
    help='SQLAlchemy DB URL; see '
         '<http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls>')  # noqa
@click.pass_context
def cli(ctx, db_url):
    """Initialize db model according to lister.

    """
    config = {}
    if db_url:
        config['db_url'] = db_url
    ctx.obj = config


@cli.command('github')
@click.option('--createdb', is_flag=True, default=False,
              help='create db')
@click.option('--dropdb', is_flag=True, default=False,
              help='Drop db')
@click.pass_context
def github(ctx, createdb, dropdb):
    from .github import models
    from .github.lister import GitHubLister

    override_conf = {'lister_db_url': ctx.obj['db_url']}

    lister = GitHubLister(lister_name='github.com',
                          api_baseurl='https://api.github.com',
                          override_config=override_conf)

    if dropdb:
        models.ModelBase.metadata.drop_all(lister.db_engine)

    if createdb:
        models.ModelBase.metadata.create_all(lister.db_engine)


@cli.command('gitlab')
@click.option('--createdb', is_flag=True, default=False,
              help='create db')
@click.option('--dropdb', is_flag=True, default=False,
              help='Drop db')
@click.pass_context
def gitlab(ctx, createdb, dropdb):
    from .gitlab import models
    from .gitlab.lister import GitlabLister

    override_conf = {'lister_db_url': ctx.obj['db_url']}

    lister = GitlabLister(lister_name='gitlab.com',
                          api_baseurl='https://gitlab.com/api/v4/',
                          override_config=override_conf)

    if dropdb:
        models.ModelBase.metadata.drop_all(lister.db_engine)

    if createdb:
        models.ModelBase.metadata.create_all(lister.db_engine)


@cli.command('bitbucket')
@click.option('--createdb', is_flag=True, default=False,
              help='create db')
@click.option('--dropdb', is_flag=True, default=False,
              help='Drop db')
@click.pass_context
def bitbucket(ctx, createdb, dropdb):
    from .bitbucket import models
    from .bitbucket.lister import BitBucketLister

    override_conf = {'lister_db_url': ctx.obj['db_url']}

    lister = BitBucketLister(lister_name='bitbucket.com',
                             api_baseurl='https://api.bitbucket.org/2.0',
                             override_config=override_conf)

    if dropdb:
        models.ModelBase.metadata.drop_all(lister.db_engine)

    if createdb:
        models.ModelBase.metadata.create_all(lister.db_engine)


if __name__ == '__main__':
    cli()
