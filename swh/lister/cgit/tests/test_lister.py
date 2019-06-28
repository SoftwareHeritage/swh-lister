# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


from urllib.parse import urlparse

from swh.lister.cgit.lister import find_netloc, get_repo_list


def test_get_repo_list():
    f = open('swh/lister/cgit/tests/response.html')
    repos = get_repo_list(f.read())
    f = open('swh/lister/cgit/tests/repo_list.txt')
    expected_repos = f.readlines()
    expected_repos = list(map((lambda repo: repo[:-1]), expected_repos))
    assert len(repos) == len(expected_repos)
    for i in range(len(repos)):
        assert str(repos[i]) == expected_repos[i]


def test_find_netloc():
    first_url = urlparse('http://git.savannah.gnu.org/cgit/')
    second_url = urlparse('https://cgit.kde.org/')

    assert find_netloc(first_url) == 'http://git.savannah.gnu.org'
    assert find_netloc(second_url) == 'https://cgit.kde.org'
