import pytest
from swh.scheduler.tests.conftest import *  # noqa


@pytest.fixture(scope='session')
def celery_includes():
    return [
        'swh.lister.bitbucket.tasks',
        'swh.lister.cgit.tasks',
        'swh.lister.cran.tasks',
        'swh.lister.debian.tasks',
        'swh.lister.github.tasks',
        'swh.lister.gitlab.tasks',
        'swh.lister.gnu.tasks',
        'swh.lister.npm.tasks',
        'swh.lister.packagist.tasks',
        'swh.lister.phabricator.tasks',
        'swh.lister.pypi.tasks',
    ]
