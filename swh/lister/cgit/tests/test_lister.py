# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


from bs4 import BeautifulSoup
from urllib.parse import urlparse

from swh.lister.cgit.lister import priority_origin_url, find_all_origin_url
from swh.lister.cgit.lister import find_netloc


def test_find_all_origin_url():
    f = open('swh/lister/cgit/tests/api_response.html')
    soup = BeautifulSoup(f.read(), features="html.parser")
    expected_output = {'https': 'https://git.savannah.gnu.org/git/'
                                'fbvbconv-py.git',
                       'ssh': 'ssh://git.savannah.gnu.org/srv/git/'
                              'fbvbconv-py.git',
                       'git': 'git://git.savannah.gnu.org/fbvbconv-py.git'}

    output = find_all_origin_url(soup)

    for protocol, url in expected_output.items():
        assert url == output[protocol]


def test_priority_origin_url():
    first_input = {'https': 'https://kernel.googlesource.com/pub/scm/docs/'
                            'man-pages/man-pages.git',
                   'git': 'git://git.kernel.org/pub/scm/docs/man-pages/'
                          'man-pages.git'}
    second_input = {'git': 'git://git.savannah.gnu.org/perl-pesel.git',
                    'ssh': 'ssh://git.savannah.gnu.org/srv/git/perl-pesel.git'}
    third_input = {}

    assert (priority_origin_url(first_input) ==
            'https://kernel.googlesource.com/pub/scm/docs/man-pages/'
            'man-pages.git')
    assert (priority_origin_url(second_input) ==
            'git://git.savannah.gnu.org/perl-pesel.git')
    assert priority_origin_url(third_input) is None


def test_find_netloc():
    first_url = urlparse('http://git.savannah.gnu.org/cgit/')
    second_url = urlparse('https://cgit.kde.org/')

    assert find_netloc(first_url) == 'http://git.savannah.gnu.org'
    assert find_netloc(second_url) == 'https://cgit.kde.org'
