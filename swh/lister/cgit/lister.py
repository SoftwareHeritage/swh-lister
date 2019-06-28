# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import random
import logging
from bs4 import BeautifulSoup
import requests
from urllib.parse import urlparse

from .models import CGitModel

from swh.lister.core.simple_lister import SimpleLister
from swh.lister.core.lister_transports import ListerOnePageApiTransport


class CGitLister(ListerOnePageApiTransport, SimpleLister):
    MODEL = CGitModel
    LISTER_NAME = 'cgit'
    PAGE = None
    url_prefix_present = True

    def __init__(self, url, instance=None, url_prefix=None,
                 override_config=None):
        """Inits Class with PAGE url and origin url prefix.

        Args:
            url (str): URL of the CGit instance.
            instance (str): Name of cgit instance.
            url_prefix (str): Prefix of the origin_url. Origin link of the
                              repos of some special instances do not match
                              the url of the repository page, they have origin
                              url in the format <url_prefix>/<repo_name>.

        """
        self.PAGE = url
        if url_prefix is None:
            self.url_prefix = url
            self.url_prefix_present = False
        else:
            self.url_prefix = url_prefix

        if not self.url_prefix.endswith('/'):
            self.url_prefix += '/'
        url = urlparse(self.PAGE)
        self.url_netloc = find_netloc(url)

        if not instance:
            instance = url.hostname
        self.instance = instance

        ListerOnePageApiTransport .__init__(self)
        SimpleLister.__init__(self, override_config=override_config)

    def list_packages(self, response):
        """List the actual cgit instance origins from the response.

        Find repositories metadata by parsing the html page (response's raw
        content). If there are links in the html page, retrieve those
        repositories metadata from those pages as well. Return the
        repositories as list of dictionaries.

        Args:
            response (Response): http api request response.

        Returns:
            List of repository origin urls (as dict) included in the response.

        """
        repos_details = []

        for repo in self.yield_repo_from_responses(response):
            repo_name = repo.a.text
            origin_url = self.find_origin_url(repo, repo_name)

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

    def yield_repo_from_responses(self, response):
        """Yield repositories from all pages of the cgit instance.

        Finds the number of pages present and yields the list of
        repositories present.

        Args:
            response (Response): server response.

        Yields:
            List of beautifulsoup object of repository rows.

        """
        html = response.text
        yield from get_repo_list(html)
        pages = self.get_pages(make_soup(html))
        if len(pages) > 1:
            yield from self.get_repos_from_pages(pages[1:])

    def find_origin_url(self, repo, repo_name):
        """Finds the origin url for a repository

        Args:
            repo (Beautifulsoup): Beautifulsoup object of the repository
                                  row present in base url.
            repo_name (str): Repository name.

        Returns:
            string: origin url.

        """
        if self.url_prefix_present:
            return self.url_prefix + repo_name

        return self.get_url(repo)

    def get_pages(self, url_soup):
        """Find URL of all pages.

        Finds URL of pages that are present by parsing over the HTML of
        pagination present at the end of the page.

        Args:
            url_soup (Beautifulsoup): a beautifulsoup object of base URL

        Returns:
            list: URL of pages present for a cgit instance

        """
        pages = url_soup.find('div', {"class": "content"}).find_all('li')

        if not pages:
            return [self.PAGE]

        return [self.get_url(page) for page in pages]

    def get_repos_from_pages(self, pages):
        """Find repos from all pages.

        Request the available repos from the pages. This yields
        the available repositories found as beautiful object representation.

        Args:
            pages ([str]): list of urls of all pages present for a
                           particular cgit instance.

        Yields:
            List of beautifulsoup object of repository (url) rows
            present in pages(except first).

        """
        for page in pages:
            response = requests.get(page)
            if not response.ok:
                logging.warning('Failed to retrieve repositories from page %s',
                                page)
                continue

            yield from get_repo_list(response.text)

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
    """Finds the network location from then url.

    URL in the repo are relative to the network location part of base
    URL, so we need to compute it to reconstruct URLs.

    Args:
        url (urllib): urllib object of url.

    Returns:
        string: Scheme and Network location part in the base URL.

    Example:
    For url = https://git.kernel.org/pub/scm/
        >>> find_netloc(url)
        'https://git.kernel.org'

    """
    return '%s://%s' % (url.scheme, url.netloc)


def get_repo_list(response):
    """Find repositories (as beautifulsoup object) available within the server
       response.

    Args:
        response (Response): server response

    Returns:
        List all repositories as beautifulsoup object within the response.

    """
    repo_soup = make_soup(response)
    return repo_soup \
        .find('div', {"class": "content"}).find_all("tr", {"class": ""})


def make_soup(response):
    """Instantiates a beautiful soup object from the response object.

    """
    return BeautifulSoup(response, features="html.parser")
