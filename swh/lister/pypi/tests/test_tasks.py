from unittest.mock import patch


def test_ping(swh_app, celery_session_worker):
    res = swh_app.send_task(
        'swh.lister.pypi.tasks.ping')
    assert res
    res.wait()
    assert res.successful()
    assert res.result == 'OK'


@patch('swh.lister.pypi.tasks.PyPILister')
def test_lister(lister, swh_app, celery_session_worker):
    # setup the mocked PypiLister
    lister.return_value = lister
    lister.run.return_value = None

    res = swh_app.send_task(
        'swh.lister.pypi.tasks.PyPIListerTask')
    assert res
    res.wait()
    assert res.successful()

    lister.assert_called_once_with()
    lister.db_last_index.assert_not_called()
    lister.run.assert_called_once_with()
