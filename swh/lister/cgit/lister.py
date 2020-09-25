# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging
import re
from typing import Any, Dict, Generator, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from requests import Session
from requests.adapters import HTTPAdapter

from swh.core.utils import grouper
from swh.lister import USER_AGENT
from swh.lister.core.lister_base import ListerBase

from .models import CGitModel

logger = logging.getLogger(__name__)


class CGitLister(ListerBase):
    """Lister class for CGit repositories.

    This lister will retrieve the list of published git repositories by
    parsing the HTML page(s) of the index retrieved at `url`.

    For each found git repository, a query is made at the given url found
    in this index to gather published "Clone" URLs to be used as origin
    URL for that git repo.

    If several "Clone" urls are provided, prefer the http/https one, if
    any, otherwise fall bak to the first one.

    A loader task is created for each git repository::

        Task:
            Type: load-git
            Policy: recurring
            Args:
                <git_clonable_url>

    Example::

        Task:
            Type: load-git
            Policy: recurring
            Args:
                'https://git.savannah.gnu.org/git/elisp-es.git'
    """

    MODEL = CGitModel
    DEFAULT_URL = "https://git.savannah.gnu.org/cgit/"
    LISTER_NAME = "cgit"
    url_prefix_present = True

    def __init__(self, url=None, instance=None, override_config=None):
        """Lister class for CGit repositories.

        Args:
            url (str): main URL of the CGit instance, i.e. url of the index
                of published git repositories on this instance.
            instance (str): Name of cgit instance. Defaults to url's hostname
                if unset.

        """
        super().__init__(override_config=override_config)

        if url is None:
            url = self.config.get("url", self.DEFAULT_URL)
        self.url = url

        if not instance:
            instance = urlparse(url).hostname
        self.instance = instance
        self.session = Session()
        self.session.mount(self.url, HTTPAdapter(max_retries=3))
        self.session.headers = {
            "User-Agent": USER_AGENT,
        }

    def run(self) -> Dict[str, str]:
        status = "uneventful"
        total = 0
        for repos in grouper(self.get_repos(), 10):
            models = list(filter(None, (self.build_model(repo) for repo in repos)))
            injected_repos = self.inject_repo_data_into_db(models)
            self.schedule_missing_tasks(models, injected_repos)
            self.db_session.commit()
            total += len(injected_repos)
            logger.debug("Scheduled %s tasks for %s", total, self.url)
            status = "eventful"

        return {"status": status}

    def get_repos(self) -> Generator[str, None, None]:
        """Generate git 'project' URLs found on the current CGit server

        """
        next_page = self.url
        while next_page:
            bs_idx = self.get_and_parse(next_page)
            for tr in bs_idx.find("div", {"class": "content"}).find_all(
                "tr", {"class": ""}
            ):
                yield urljoin(self.url, tr.find("a")["href"])

            try:
                pager = bs_idx.find("ul", {"class": "pager"})
                current_page = pager.find("a", {"class": "current"})
                if current_page:
                    next_page = current_page.parent.next_sibling.a["href"]
                    next_page = urljoin(self.url, next_page)
            except (AttributeError, KeyError):
                # no pager, or no next page
                next_page = None

    def build_model(self, repo_url: str) -> Optional[Dict[str, Any]]:
        """Given the URL of a git repo project page on a CGit server,
        return the repo description (dict) suitable for insertion in the db.
        """
        bs = self.get_and_parse(repo_url)
        urls = [x["href"] for x in bs.find_all("a", {"rel": "vcs-git"})]

        if not urls:
            return None

        # look for the http/https url, if any, and use it as origin_url
        for url in urls:
            if urlparse(url).scheme in ("http", "https"):
                origin_url = url
                break
        else:
            # otherwise, choose the first one
            origin_url = urls[0]

        return {
            "uid": repo_url,
            "name": bs.find("a", title=re.compile(".+"))["title"],
            "origin_type": "git",
            "instance": self.instance,
            "origin_url": origin_url,
        }

    def get_and_parse(self, url: str) -> BeautifulSoup:
        "Get the given url and parse the retrieved HTML using BeautifulSoup"
        return BeautifulSoup(self.session.get(url).text, features="html.parser")
