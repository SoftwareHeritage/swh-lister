# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import random
from bs4 import BeautifulSoup
from collections import defaultdict
import requests
from urllib.parse import urlparse

from .models import CGitModel

from swh.lister.core.simple_lister import SimpleLister
from swh.lister.core.lister_transports import ListerOnePageApiTransport


class CGitLister(ListerOnePageApiTransport, SimpleLister):
    MODEL = CGitModel
    LISTER_NAME = 'cgit'
    PAGE = None

    def __init__(self, base_url, instance=None, override_config=None):

        self.PAGE = base_url
        url = urlparse(self.PAGE)
        self.url_netloc = find_netloc(url)

        if not instance:
            instance = url.hostname
        self.instance = instance
        ListerOnePageApiTransport .__init__(self)
        SimpleLister.__init__(self, override_config=override_config)

    def list_packages(self, response):
        """List the actual cgit instance origins from the response.

        Find the repos in all the pages by parsing over the HTML of
        the `base_url`. Find the details for all the repos and return
        them in the format of list of dictionaries.

        """
        repos_details = []
        repos = get_repo_list(response)
        soup = make_repo_soup(response)
        pages = self.get_page(soup)
        if len(pages) > 1:
            repos.extend(self.get_all_pages(pages))

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

    def get_page(self, soup):
        """Find URL of all pages

        Finds URL of all the pages that are present by parsing over the HTML of
        pagination present at the end of the page.

        Args:
            soup (Beautifulsoup): a beautifulsoup object of base URL

        Returns:
            list: URL of all the pages present for a cgit instance

        """
        pages = soup.find('div', {"class": "content"}).find_all('li')

        if not pages:
            return [self.PAGE]

        return [self.get_url(page) for page in pages]

    def get_all_pages(self, pages):
        """Find repos from all the pages

        Make the request for all the pages (except the first) present for a
        particular cgit instance and finds the repos that are available
        for each and every page.

        Args:
            pages ([str]): list of urls of all the pages present for a
                           particular cgit instance

        Returns:
            List of beautifulsoup object of all the repositories (url) row
            present in all the pages(except first).

        """
        all_repos = []
        for page in pages[1:]:
            response = requests.get(page)
            repos = get_repo_list(response)
            all_repos.extend(repos)

        return all_repos

    def get_url(self, repo):
        """Finds url of a repo page.

        Finds the url of a repo page by parsing over the html of the row of
        that repo present in the base url.

        Args:
            repo (Beautifulsoup): a beautifulsoup object of the repository
                                  row present in base url.

        Returns:
            string: The url of a repo.

        """
        suffix = repo.a['href']
        return self.url_netloc + suffix

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
            'instance': self.instance,
        }

    def transport_response_simplified(self, repos_details):
        """Transform response to list for model manipulation.

        """
        return [self.get_model_from_repo(repo) for repo in repos_details]


def find_netloc(url):
    """Finds the network location from then base_url

    All the url in the repo are relative to the network location part of base
    url, so we need to compute it to reconstruct all the urls.

    Args:
        url (urllib): urllib object of base_url

    Returns:
        string: Scheme and Network location part in the base URL.

    Example:
    For base_url = https://git.kernel.org/pub/scm/
        >>> find_netloc(url)
        'https://git.kernel.org'

    """
    return '%s://%s' % (url.scheme, url.netloc)


def get_repo_list(response):
    """Find all the rows with repo for a particualar page on the base url

    Finds all the repos on page and retuens a list of all the repos. Each
    element of the list is a beautifulsoup object representing a repo.

    Args:
        response (Response): server response

    Returns:
        List of all the repos on a page.

    """
    repo_soup = make_repo_soup(response)
    return repo_soup \
        .find('div', {"class": "content"}).find_all("tr", {"class": ""})


def make_repo_soup(response):
    """Makes BeautifulSoup object of the response

    """
    return BeautifulSoup(response.text, features="html.parser")


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
    repo_soup = make_repo_soup(response)

    origin_urls = find_all_origin_url(repo_soup)
    return priority_origin_url(origin_urls)


def find_all_origin_url(soup):
    """Finds all possible origin url for a repo.

    Finds all the origin url for a particular repo by parsing over the html of
    repo page.

    Args:
        soup: a beautifulsoup object repo representation.

    Returns:
        dictionary: All possible origin urls for a repository (dict with
                    key 'protocol', value the associated url).

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
        origin_urls (Dict): All possible origin urls for a repository
                            (key 'protocol', value the associated url)

    Returns:
        Url (str) with the highest priority.

    """
    for protocol in ['https', 'http', 'git', 'ssh']:
        if protocol in origin_url:
            return origin_url[protocol]
