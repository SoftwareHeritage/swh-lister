
def test_ping(swh_app, celery_session_worker):
    res = swh_app.send_task(
        'swh.lister.phabricator.tasks.ping')
    assert res
    res.wait()
    assert res.successful()
    assert res.result == 'OK'
