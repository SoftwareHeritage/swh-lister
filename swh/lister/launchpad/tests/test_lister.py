def test_launchpad_lister(lister_launchpad, datadir):

    lister_launchpad.run()

    assert (
        len(lister_launchpad.launchpad.git_repositories.getRepositories.mock_calls) == 3
    )

    r = lister_launchpad.scheduler.search_tasks(task_type="load-git")
    assert len(r) == 30

    for row in r:
        assert row["type"] == "load-git"
        # arguments check
        args = row["arguments"]["args"]
        assert len(args) == 0

        # kwargs
        kwargs = row["arguments"]["kwargs"]
        assert set(kwargs.keys()) == {"url"}

        url = kwargs["url"]
        assert url.startswith("https://git.launchpad.net")

        assert row["policy"] == "recurring"
        assert row["priority"] is None
        assert row["retries_left"] == 0
