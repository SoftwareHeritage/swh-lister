# Copyright (C) 2017-2021 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from dataclasses import asdict, dataclass
from datetime import datetime
import logging
import random
from typing import Any, Dict, Iterator, List, Optional
from urllib import parse

import iso8601
import requests
from tenacity.before_sleep import before_sleep_log

from swh.lister.utils import throttling_retry
from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from .. import USER_AGENT
from ..pattern import CredentialsType, Lister

logger = logging.getLogger(__name__)


@dataclass
class BitbucketListerState:
    """State of Bitbucket lister"""

    last_repo_cdate: Optional[datetime] = None
    """Creation date and time of the last listed repository during an
    incremental pass"""


class BitbucketLister(Lister[BitbucketListerState, List[Dict[str, Any]]]):
    """List origins from Bitbucket using its REST API.

    Bitbucket API has the following rate-limit configuration:

      * 60 requests per hour for anonymous users

      * 1000 requests per hour for authenticated users

    The lister is working in anonymous mode by default but Bitbucket account
    credentials can be provided to perform authenticated requests.
    """

    LISTER_NAME = "bitbucket"
    INSTANCE = "bitbucket"

    API_URL = "https://api.bitbucket.org/2.0/repositories"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        page_size: int = 1000,
        incremental: bool = True,
        credentials: CredentialsType = None,
    ):
        super().__init__(
            scheduler=scheduler,
            credentials=credentials,
            url=self.API_URL,
            instance=self.INSTANCE,
        )

        self.incremental = incremental

        self.url_params = {
            "pagelen": page_size,
            # only return needed JSON fields in bitbucket API responses
            # (also prevent errors 500 when listing)
            "fields": (
                "next,values.links.clone.href,values.scm,values.updated_on,"
                "values.created_on"
            ),
        }

        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/json", "User-Agent": USER_AGENT}
        )

        if len(self.credentials) > 0:
            cred = random.choice(self.credentials)
            logger.warning("Using Bitbucket credentials from user %s", cred["username"])
            self.set_credentials(cred["username"], cred["password"])
        else:
            logger.warning("No credentials set in configuration, using anonymous mode")

    def state_from_dict(self, d: Dict[str, Any]) -> BitbucketListerState:
        last_repo_cdate = d.get("last_repo_cdate")
        if last_repo_cdate is not None:
            d["last_repo_cdate"] = iso8601.parse_date(last_repo_cdate)
        return BitbucketListerState(**d)

    def state_to_dict(self, state: BitbucketListerState) -> Dict[str, Any]:
        d = asdict(state)
        last_repo_cdate = d.get("last_repo_cdate")
        if last_repo_cdate is not None:
            d["last_repo_cdate"] = last_repo_cdate.isoformat()
        return d

    def set_credentials(self, username: Optional[str], password: Optional[str]) -> None:
        """Set basic authentication headers with given credentials."""
        if username is not None and password is not None:
            self.session.auth = (username, password)

    @throttling_retry(before_sleep=before_sleep_log(logger, logging.DEBUG))
    def page_request(self, last_repo_cdate: str) -> requests.Response:

        self.url_params["after"] = last_repo_cdate
        logger.debug("Fetching URL %s with params %s", self.url, self.url_params)

        response = self.session.get(self.url, params=self.url_params)

        if response.status_code != 200:
            logger.warning(
                "Unexpected HTTP status code %s on %s: %s",
                response.status_code,
                response.url,
                response.content,
            )
        response.raise_for_status()

        return response

    def get_pages(self) -> Iterator[List[Dict[str, Any]]]:

        last_repo_cdate: str = "1970-01-01"
        if (
            self.incremental
            and self.state is not None
            and self.state.last_repo_cdate is not None
        ):
            last_repo_cdate = self.state.last_repo_cdate.isoformat()

        while True:
            body = self.page_request(last_repo_cdate).json()

            yield body["values"]

            next_page_url = body.get("next")
            if next_page_url is not None:
                next_page_url = parse.urlparse(next_page_url)
                if not next_page_url.query:
                    logger.warning("Failed to parse url %s", next_page_url)
                    break
                last_repo_cdate = parse.parse_qs(next_page_url.query)["after"][0]
            else:
                # last page
                break

    def get_origins_from_page(
        self, page: List[Dict[str, Any]]
    ) -> Iterator[ListedOrigin]:
        """Convert a page of Bitbucket repositories into a list of ListedOrigins.

        """
        assert self.lister_obj.id is not None

        for repo in page:
            last_update = iso8601.parse_date(repo["updated_on"])
            origin_url = repo["links"]["clone"][0]["href"]
            origin_type = repo["scm"]

            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                url=origin_url,
                visit_type=origin_type,
                last_update=last_update,
            )

    def commit_page(self, page: List[Dict[str, Any]]) -> None:
        """Update the currently stored state using the latest listed page."""
        if self.incremental:
            last_repo = page[-1]
            last_repo_cdate = iso8601.parse_date(last_repo["created_on"])

            if (
                self.state.last_repo_cdate is None
                or last_repo_cdate > self.state.last_repo_cdate
            ):
                self.state.last_repo_cdate = last_repo_cdate

    def finalize(self) -> None:
        if self.incremental:
            scheduler_state = self.get_state_from_scheduler()

            if self.state.last_repo_cdate is None:
                return

            # Update the lister state in the backend only if the last seen id of
            # the current run is higher than that stored in the database.
            if (
                scheduler_state.last_repo_cdate is None
                or self.state.last_repo_cdate > scheduler_state.last_repo_cdate
            ):
                self.updated = True
