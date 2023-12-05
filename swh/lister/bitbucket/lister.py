# Copyright (C) 2017-2023 The Software Heritage developers
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
from requests import HTTPError

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, Lister

logger = logging.getLogger(__name__)


@dataclass
class BitbucketListerState:
    """State of Bitbucket lister"""

    last_repo_cdate: Optional[datetime] = None
    """Creation date and time of the last listed repository during an
    incremental pass"""


class BitbucketLister(Lister[BitbucketListerState, List[Dict[str, Any]]]):
    """List origins from Bitbucket using its API.

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
        url: str = API_URL,
        instance: str = INSTANCE,
        page_size: int = 1000,
        incremental: bool = True,
        credentials: CredentialsType = None,
        max_origins_per_page: Optional[int] = None,
        max_pages: Optional[int] = None,
        enable_origins: bool = True,
    ):
        super().__init__(
            scheduler=scheduler,
            credentials=credentials,
            url=url,
            instance=instance,
            max_origins_per_page=max_origins_per_page,
            max_pages=max_pages,
            enable_origins=enable_origins,
        )

        self.incremental = incremental

        self.url_params: Dict[str, Any] = {
            "pagelen": page_size,
            # only return needed JSON fields in bitbucket API responses
            # (also prevent errors 500 when listing)
            "fields": (
                "next,values.links.clone.href,values.scm,values.updated_on,"
                "values.created_on"
            ),
        }

        self.session.headers.update({"Accept": "application/json"})

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

    def get_pages(self) -> Iterator[List[Dict[str, Any]]]:
        last_repo_cdate: str = "1970-01-01"
        if (
            self.incremental
            and self.state is not None
            and self.state.last_repo_cdate is not None
        ):
            last_repo_cdate = self.state.last_repo_cdate.isoformat()

        while True:
            self.url_params["after"] = last_repo_cdate
            try:
                body = self.http_request(self.url, params=self.url_params).json()
                yield body["values"]
            except HTTPError as e:
                if e.response is not None and e.response.status_code == 500:
                    logger.warning(
                        "URL %s is buggy (error 500), skip it and get next page.",
                        e.response.url,
                    )
                    body = self.http_request(
                        self.url,
                        params={
                            "pagelen": self.url_params["pagelen"],
                            "fields": "next",
                        },
                    ).json()

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
        """Convert a page of Bitbucket repositories into a list of ListedOrigins."""
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
