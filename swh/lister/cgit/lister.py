# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import random
from bs4 import BeautifulSoup
from collections import defaultdict
import requests
import urllib.parse

from .models import CGitModel

from swh.lister.core.simple_lister import SimpleLister
from swh.lister.core.lister_transports import ListerOnePageApiTransport


class CGitLister(ListerOnePageApiTransport, SimpleLister):
    MODEL = CGitModel
    LISTER_NAME = 'cgit'
    PAGE = ''

    def __init__(self, base_url, instance=None, override_config=None):
        if not base_url.endswith('/'):
            base_url = base_url+'/'
        self.PAGE = base_url

        # This part removes any suffix from the base url and stores it in
        # next_url. For example for base_url = https://git.kernel.org/pub/scm/
        # it will convert it into https://git.kernel.org and then attach
        # the suffix
        (part1, part2, next_url) = self.PAGE.split('/', 2)
        self.next_url = part1 + '//' + next_url

        if not instance:
            instance = urllib.parse.urlparse(base_url).hostname
        self.instance = instance
        ListerOnePageApiTransport .__init__(self)
        SimpleLister.__init__(self, override_config=override_config)

    def list_packages(self, response):
        """List the actual cgit instance origins from the response.

        """
        repos_details = []
        soup = BeautifulSoup(response.text, features="html.parser") \
            .find('div', {"class": "content"})
        repos = soup.find_all("tr", {"class": ""})
        for repo in repos:
            repo_name = repo.a.text
            repo_url = self.get_url(repo)
            origin_url = find_origin_url(repo_url)

            try:
                time = repo.span['title']
            except Exception:
                time = None

            if origin_url is not None:
                repos_details.append({
                                        'name': repo_name,
                                        'time': time,
                                        'origin_url': origin_url,
                                    })

        random.shuffle(repos_details)
        return repos_details

    def get_url(self, repo):
        """Finds url of a repo page.

        Finds the url of a repo page by parsing over the html of the row of
        that repo present in the base url.

        Args:
            repo: a beautifulsoup object of the html code of the repo row
                   present in base url.

        Returns:
            string: The url of a repo.
        """
        suffix = repo.a['href']
        return self.next_url + suffix

    def get_model_from_repo(self, repo):
        """Transform from repository representation to model.

        """
        return {
            'uid': self.PAGE + repo['name'],
            'name': repo['name'],
            'full_name': repo['name'],
            'html_url': repo['origin_url'],
            'origin_url': repo['origin_url'],
            'origin_type': 'git',
            'time_updated': repo['time'],
        }

    def transport_response_simplified(self, response):
        """Transform response to list for model manipulation.

        """
        return [self.get_model_from_repo(repo) for repo in response]


def find_origin_url(repo_url):
    """Finds origin url for a repo.

    Finds the origin url for a particular repo by parsing over the page of
    that repo.

    Args:
        repo_url: URL of the repo.

    Returns:
        string: Origin url for the repo.

    Examples:

        >>> find_origin_url(
            'http://git.savannah.gnu.org/cgit/fbvbconv-py.git/')
        'https://git.savannah.gnu.org/git/fbvbconv-py.git'

    """

    response = requests.get(repo_url)
    soup = BeautifulSoup(response.text, features="html.parser")

    origin_urls = find_all_origin_url(soup)
    return priority_origin_url(origin_urls)


def find_all_origin_url(soup):
    """
    Finds all the origin url for a particular repo by parsing over the html of
    repo page.

    Args:
        soup: a beautifulsoup object of the html code of the repo.

    Returns:
        dictionary: All possible origin urls with their protocol as key.

    Examples:
        If soup is beautifulsoup object of the html code at
        http://git.savannah.gnu.org/cgit/fbvbconv-py.git/

        >>> print(find_all_origin_url(soup))
        { 'https': 'https://git.savannah.gnu.org/git/fbvbconv-py.git',
          'ssh': 'ssh://git.savannah.gnu.org/srv/git/fbvbconv-py.git',
          'git': 'git://git.savannah.gnu.org/fbvbconv-py.git'}
    """
    origin_urls = defaultdict(dict)
    found_clone_word = False

    for i in soup.find_all('tr'):
        if found_clone_word:
            link = i.text
            protocol = link[:link.find(':')]
            origin_urls[protocol] = link
        if i.text == 'Clone':
            found_clone_word = True

    return origin_urls


def priority_origin_url(origin_url):
    """Finds the highest priority link for a particular repo.

    Priority order is https>http>git>ssh.

    Args:
        origin_urls: A dictionary of origin links with their protocol as key.

    Returns:
        string: URL with the highest priority.

    """
    for protocol in ['https', 'http', 'git', 'ssh']:
        if protocol in origin_url:
            return origin_url[protocol]
