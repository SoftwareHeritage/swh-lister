from unittest.mock import patch


@patch("swh.lister.launchpad.tasks.LaunchpadLister")
def test_new(lister, swh_app, celery_session_worker):
    # setup the mocked LaunchpadLister
    lister.return_value = lister
    lister.run.return_value = None

    res = swh_app.send_task("swh.lister.launchpad.tasks.NewLaunchpadLister")
    assert res
    res.wait()
    assert res.successful()

    assert lister.call_count == 2
    lister.db_last_threshold.assert_called_once()
    lister.run.assert_called_once()


@patch("swh.lister.launchpad.tasks.LaunchpadLister")
def test_full(lister, swh_app, celery_session_worker):
    # setup the mocked LaunchpadLister
    lister.return_value = lister
    lister.run.return_value = None

    res = swh_app.send_task("swh.lister.launchpad.tasks.FullLaunchpadLister")
    assert res
    res.wait()
    assert res.successful()

    lister.assert_called_once()
    lister.db_last_threshold.assert_not_called()
    lister.run.assert_called_once_with(max_bound=None)