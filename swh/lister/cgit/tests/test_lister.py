# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


def test_lister_no_page(requests_mock_datadir, swh_listers):
    lister = swh_listers['cgit']

    assert lister.url == 'https://git.savannah.gnu.org/cgit/'

    repos = list(lister.get_repos())
    assert len(repos) == 977

    assert repos[0] == 'https://git.savannah.gnu.org/cgit/elisp-es.git/'
    # note the url below is NOT a subpath of /cgit/
    assert repos[-1] == 'https://git.savannah.gnu.org/path/to/yetris.git/'  # noqa
    # note the url below is NOT on the same server
    assert repos[-2] == 'http://example.org/cgit/xstarcastle.git/'


def test_lister_model(requests_mock_datadir, swh_listers):
    lister = swh_listers['cgit']

    repo = next(lister.get_repos())

    model = lister.build_model(repo)
    assert model == {
        'uid': 'https://git.savannah.gnu.org/cgit/elisp-es.git/',
        'name': 'elisp-es.git',
        'origin_type': 'git',
        'instance': 'git.savannah.gnu.org',
        'origin_url': 'https://git.savannah.gnu.org/git/elisp-es.git'
        }


def test_lister_with_pages(requests_mock_datadir, swh_listers):
    lister = swh_listers['cgit']
    lister.url = 'https://git.tizen/cgit/'

    repos = list(lister.get_repos())
    # we should have 16 repos (listed on 3 pages)
    assert len(repos) == 16


def test_lister_run(requests_mock_datadir, swh_listers):
    lister = swh_listers['cgit']
    lister.url = 'https://git.tizen/cgit/'
    lister.run()

    r = lister.scheduler.search_tasks(task_type='load-git')
    assert len(r) == 16

    for row in r:
        assert row['type'] == 'load-git'
        # arguments check
        args = row['arguments']['args']
        assert len(args) == 1

        url = args[0]
        assert url.startswith('https://git.tizen')

        # kwargs
        kwargs = row['arguments']['kwargs']
        assert kwargs == {}
        assert row['policy'] == 'recurring'
        assert row['priority'] is None
