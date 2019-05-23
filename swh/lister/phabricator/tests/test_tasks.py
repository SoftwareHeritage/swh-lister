from unittest.mock import patch


def test_ping(swh_app, celery_session_worker):
    res = swh_app.send_task(
        'swh.lister.phabricator.tasks.ping')
    assert res
    res.wait()
    assert res.successful()
    assert res.result == 'OK'


@patch('swh.lister.phabricator.tasks.PhabricatorLister')
def test_incremental(lister, swh_app, celery_session_worker):
    # setup the mocked PhabricatorLister
    lister.return_value = lister
    lister.db_last_index.return_value = 42
    lister.run.return_value = None

    res = swh_app.send_task(
        'swh.lister.phabricator.tasks.IncrementalPhabricatorLister')
    assert res
    res.wait()
    assert res.successful()

    lister.assert_called_once_with(
        api_token='', forge_url='https://forge.softwareheritage.org')
    lister.db_last_index.assert_called_once_with()
    lister.run.assert_called_once_with(min_bound=42)
