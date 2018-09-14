# Copyright (C) 2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import click


SUPPORTED_LISTERS = ['github', 'gitlab', 'bitbucket', 'debian', 'pypi']


@click.command()
@click.option(
    '--db-url', '-d', default='postgres:///lister-gitlab.com',
    help='SQLAlchemy DB URL; see '
         '<http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls>')  # noqa
@click.option('--lister', required=1,
              type=click.Choice(SUPPORTED_LISTERS),
              help='Lister to act upon')
@click.option('--create-tables', is_flag=True, default=False,
              help='create tables')
@click.option('--drop-tables', is_flag=True, default=False,
              help='Drop tables')
@click.option('--with-data', is_flag=True, default=False,
              help='Insert minimum required data')
def cli(db_url, lister, create_tables, drop_tables, with_data):
    """Initialize db model according to lister.

    """
    override_conf = {'lister_db_url': db_url}

    insert_minimum_data = None

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

        def insert_minimum_data(lister):
            from swh.storage.schemata.distribution import Distribution, Area
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

    else:
        raise ValueError('Only supported listers are %s' % SUPPORTED_LISTERS)

    if drop_tables:
        ModelBase.metadata.drop_all(_lister.db_engine)

    if create_tables:
        ModelBase.metadata.create_all(_lister.db_engine)

        if with_data and insert_minimum_data:
            insert_minimum_data(_lister)


if __name__ == '__main__':
    cli()
