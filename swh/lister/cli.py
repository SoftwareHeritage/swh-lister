# Copyright (C) 2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import click


@click.command()
@click.option(
    '--db-url', '-d', default='postgres:///lister-gitlab.com',
    help='SQLAlchemy DB URL; see '
         '<http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls>')  # noqa
@click.option('--lister', required=1,
              type=click.Choice(['github', 'gitlab', 'bitbucket', 'debian']),
              help='Lister to act upon')
@click.option('--create-tables', is_flag=True, default=False,
              help='create tables')
@click.option('--drop-tables', is_flag=True, default=False,
              help='Drop tables')
def cli(db_url, lister, create_tables, drop_tables):
    """Initialize db model according to lister.

    """
    supported_listers = ['github', 'gitlab', 'bitbucket', 'debian']
    override_conf = {'lister_db_url': db_url}

    if lister == 'github':
        from .github.models import IndexingModelBase as ModelBase
        from .github.lister import GitHubLister

        _lister = GitHubLister(api_baseurl='https://api.github.com',
                               override_config=override_conf)
    elif lister == 'bitbucket':
        from .bitbucket.models import IndexingModelBase as ModelBase
        from .bitbucket.lister import BitBucketLister
        _lister = BitBucketLister(api_baseurl='https://api.bitbucket.org/2.0',
                                  override_config=override_conf)

    elif lister == 'gitlab':
        from .gitlab.models import ModelBase
        from .gitlab.lister import GitLabLister
        _lister = GitLabLister(api_baseurl='https://gitlab.com/api/v4/',
                               override_config=override_conf)
    elif lister == 'debian':
        from .debian.lister import DebianLister
        ModelBase = DebianLister.MODEL
        _lister = DebianLister()

    else:
        raise ValueError('Only supported listers are %s' % supported_listers)

    if drop_tables:
        ModelBase.metadata.drop_all(_lister.db_engine)

    if create_tables:
        ModelBase.metadata.create_all(_lister.db_engine)


if __name__ == '__main__':
    cli()
