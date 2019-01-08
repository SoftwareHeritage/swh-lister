import pytest


@pytest.fixture(scope='session')
def celery_enable_logging():
    return True


@pytest.fixture(scope='session')
def celery_includes():
    return [
        'swh.lister.bitbucket.tasks',
        'swh.lister.github.tasks',
    ]


# override the celery_session_app fixture to monkeypatch the 'main'
# swh.scheduler.celery_backend.config.app Celery application
# with the test application.
@pytest.fixture(scope='session')
def swh_app(celery_session_app):
    import swh.scheduler.celery_backend.config
    swh.scheduler.celery_backend.config.app = celery_session_app
    yield celery_session_app
