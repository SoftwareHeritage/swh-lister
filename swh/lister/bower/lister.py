# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information
import logging
from typing import Any, Dict, Iterator, List, Optional

import requests
from tenacity.before_sleep import before_sleep_log

from swh.lister.utils import throttling_retry
from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from .. import USER_AGENT
from ..pattern import CredentialsType, StatelessLister

logger = logging.getLogger(__name__)

# Aliasing the page results returned by `get_pages` method from the lister.
BowerListerPage = List[Dict[str, str]]


class BowerLister(StatelessLister[BowerListerPage]):
    """List Bower (Javascript package manager) origins."""

    LISTER_NAME = "bower"
    VISIT_TYPE = "git"  # Bower origins url are Git repositories
    INSTANCE = "bower"

    API_URL = "https://registry.bower.io/packages"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        credentials: Optional[CredentialsType] = None,
    ):
        super().__init__(
            scheduler=scheduler,
            credentials=credentials,
            instance=self.INSTANCE,
            url=self.API_URL,
        )
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            }
        )

    @throttling_retry(before_sleep=before_sleep_log(logger, logging.WARNING))
    def page_request(self, url: str, params: Dict[str, Any]) -> requests.Response:

        logger.info("Fetching URL %s with params %s", url, params)

        response = self.session.get(url, params=params)
        if response.status_code != 200:
            logger.warning(
                "Unexpected HTTP status code %s on %s: %s",
                response.status_code,
                response.url,
                response.content,
            )
        response.raise_for_status()

        return response

    def get_pages(self) -> Iterator[BowerListerPage]:
        """Yield an iterator which returns 'page'

        It uses the api endpoint provided by `https://registry.bower.io/packages`
        to get a list of package names with an origin url that corresponds to Git
        repository.

        There is only one page that list all origins urls.
        """
        response = self.page_request(url=self.url, params={})
        yield response.json()

    def get_origins_from_page(self, page: BowerListerPage) -> Iterator[ListedOrigin]:
        """Iterate on all pages and yield ListedOrigin instances."""
        assert self.lister_obj.id is not None

        for entry in page:
            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                visit_type=self.VISIT_TYPE,
                url=entry["url"],
                last_update=None,
            )
