import pytest
from swh.scheduler.tests.conftest import *  # noqa


@pytest.fixture(scope='session')
def celery_includes():
    return [
        'swh.lister.bitbucket.tasks',
        'swh.lister.debian.tasks',
        'swh.lister.github.tasks',
        'swh.lister.gitlab.tasks',
        'swh.lister.npm.tasks',
        'swh.lister.pypi.tasks',
        'swh.lister.phabricator.tasks',
    ]
