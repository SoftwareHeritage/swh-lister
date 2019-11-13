# Copyright (C) 2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import glob
import pytest
import traceback
from datetime import timedelta

import yaml

from swh.core.utils import numfile_sortkey as sortkey
from swh.scheduler import get_scheduler
from swh.scheduler.tests.conftest import DUMP_FILES

from swh.lister.core.lister_base import ListerBase
from swh.lister.cli import lister as cli, get_lister, SUPPORTED_LISTERS

from .test_utils import init_db
from click.testing import CliRunner


@pytest.fixture
def swh_scheduler_config(request, postgresql_proc, postgresql):
    scheduler_config = {
        'db': 'postgresql://{user}@{host}:{port}/{dbname}'.format(
            host=postgresql_proc.host,
            port=postgresql_proc.port,
            user='postgres',
            dbname='tests')
    }

    all_dump_files = sorted(glob.glob(DUMP_FILES), key=sortkey)

    cursor = postgresql.cursor()
    for fname in all_dump_files:
        with open(fname) as fobj:
            cursor.execute(fobj.read())
    postgresql.commit()

    return scheduler_config


def test_get_lister_wrong_input():
    """Unsupported lister should raise"""
    with pytest.raises(ValueError) as e:
        get_lister('unknown', 'db-url')

    assert "Invalid lister" in str(e.value)


def test_get_lister():
    """Instantiating a supported lister should be ok

    """
    db_url = init_db().url()
    for lister_name in SUPPORTED_LISTERS:
        lst = get_lister(lister_name, db_url)
        assert isinstance(lst, ListerBase)


def test_get_lister_override():
    """Overriding the lister configuration should populate its config

    """
    db_url = init_db().url()

    listers = {
        'gitlab': 'https://other.gitlab.uni/api/v4/',
        'phabricator': 'https://somewhere.org/api/diffusion.repository.search',
        'cgit': 'https://some.where/cgit',
    }

    # check the override ends up defined in the lister
    for lister_name, url in listers.items():
        lst = get_lister(
            lister_name, db_url, **{
                'url': url,
                'priority': 'high',
                'policy': 'oneshot',
            })

        assert lst.url == url
        assert lst.config['priority'] == 'high'
        assert lst.config['policy'] == 'oneshot'

    # check the default urls are used and not the override (since it's not
    # passed)
    for lister_name, url in listers.items():
        lst = get_lister(lister_name, db_url)

        # no override so this does not end up in lister's configuration
        assert 'url' not in lst.config
        assert 'priority' not in lst.config
        assert 'oneshot' not in lst.config
        assert lst.url == lst.DEFAULT_URL


def test_task_types(swh_scheduler_config, tmp_path):
    configfile = tmp_path / 'config.yml'
    config = {
        'scheduler': {
            'cls': 'local',
            'args': swh_scheduler_config
        }
    }
    configfile.write_text(yaml.dump(config))
    runner = CliRunner()
    result = runner.invoke(cli, [
        '--config-file', configfile.as_posix(),
        'register-task-types'])

    assert result.exit_code == 0, traceback.print_exception(*result.exc_info)

    scheduler = get_scheduler(**config['scheduler'])
    all_tasks = [
        'list-bitbucket-full', 'list-bitbucket-incremental',
        'list-cran',
        'list-cgit',
        'list-debian-distribution',
        'list-gitlab-full', 'list-gitlab-incremental',
        'list-github-full', 'list-github-incremental',
        'list-gnu-full',
        'list-npm-full', 'list-npm-incremental',
        'list-phabricator-full',
        'list-packagist',
        'list-pypi',
    ]
    for task in all_tasks:
        task_type_desc = scheduler.get_task_type(task)
        assert task_type_desc
        assert task_type_desc['type'] == task
        assert task_type_desc['backoff_factor'] == 1

        if task == 'list-npm-full':
            delay = timedelta(days=7)  # overloaded in the plugin registry
        elif task.endswith('-full'):
            delay = timedelta(days=90)  # default value for 'full' lister tasks
        else:
            delay = timedelta(days=1)  # default value for other lister tasks
        assert task_type_desc['default_interval'] == delay, task
