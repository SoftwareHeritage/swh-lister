# Copyright (C) 2017-2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from abc import ABC, abstractmethod
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

from ..pattern import (
    BackendStateType,
    CredentialsType,
    Lister,
    StatelessLister,
    StateType,
)

logger = logging.getLogger(__name__)

Page = Dict[str, Any]
Repository = Dict[str, Any]
Repositories = List[Repository]


class BitbucketLister(Lister[StateType, Repositories], ABC):
    """Commonalities between Bitbucket instance types"""

    LISTER_NAME = "bitbucket"
    CLOUD_INSTANCES = (None, "", "bitbucket", "bitbucket.org")
    CLONES = ["https", "http", "ssh"]

    URL_PARAMS: Dict[str, Any]
    THIS_PAGE: str
    LEN_PAGE: str
    NEXT_PAGE: str
    SCM: str

    api_url: str

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: Optional[str] = None,
        instance: Optional[str] = None,
        page_size: int = 1000,
        credentials: CredentialsType = None,
        max_origins_per_page: Optional[int] = None,
        max_pages: Optional[int] = None,
        enable_origins: bool = True,
        **kwargs,
    ):
        super().__init__(
            scheduler=scheduler,
            credentials=credentials,
            url=url,
            instance=instance,
            max_origins_per_page=max_origins_per_page,
            max_pages=max_pages,
            enable_origins=enable_origins,
            **kwargs,
        )

        self.url_params: Dict[str, Any] = {
            self.LEN_PAGE: page_size,
        } | self.URL_PARAMS

        self.session.headers.update({"Accept": "application/json"})

        if len(self.credentials) > 0:
            cred = random.choice(self.credentials)
            logger.warning("Using Bitbucket credentials from user %s", cred["username"])
            self.set_credentials(cred["username"], cred["password"])
        else:
            logger.warning("No credentials set in configuration, using anonymous mode")

    def set_credentials(self, username: Optional[str], password: Optional[str]) -> None:
        """Set basic authentication headers with given credentials."""
        if username is not None and password is not None:
            self.session.auth = (username, password)

    def get_pages(self) -> Iterator[Repositories]:
        page = self.initial_page()

        while True:
            self.url_params[self.THIS_PAGE] = page
            try:
                body = self.http_request(self.api_url, params=self.url_params).json()
                yield body["values"]
            except HTTPError as e:
                if e.response is not None and e.response.status_code >= 500:
                    logger.warning(
                        "URL %s is buggy (error %s), skip it and get next page.",
                        e.response.url,
                        e.response.status_code,
                    )
                    body = self.http_request(
                        self.api_url, params=self.error_url_params(body, page)
                    ).json()

            page = self.next_page(body)
            if page is None:
                break

    def get_origins_from_page(self, page: Repositories) -> Iterator[ListedOrigin]:
        """Convert a page of Bitbucket repositories into a list of ListedOrigins."""
        assert self.lister_obj.id is not None

        for repo in page:
            last_update = self.get_last_update(repo)
            urls = {lnk["name"]: lnk["href"] for lnk in repo["links"]["clone"]}
            origin_url = [urls[c] for c in self.CLONES if urls.get(c)][0]
            origin_type = repo.get(self.SCM, "git")
            enabled = self.get_enabled(repo)

            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                url=origin_url,
                visit_type=origin_type,
                last_update=last_update,
                enabled=enabled,
            )

    @abstractmethod
    def page_url(self, page: Optional[int] = None) -> Optional[str]:
        """Optionally return the URL for a specific page if appropriate."""

    @abstractmethod
    def initial_page(self) -> Any:
        """Return the initial page"""

    @abstractmethod
    def next_page(self, body: Page) -> Any:
        "Return the next page from the current page"

    @abstractmethod
    def error_url_params(self, body: Page, page: Any) -> Dict[str, Any]:
        """Return the URL params to use on error"""

    @abstractmethod
    def get_last_update(self, repo: Repository):
        """Optionally return the date a repo last changed"""

    @abstractmethod
    def get_enabled(self, repo: Repository) -> bool:
        """Return whether or not the repo should be downloaded"""

    @classmethod
    def from_config(
        cls,
        scheduler: Dict[str, Any],
        instance: Optional[str] = None,
        url: Optional[str] = None,
        incremental: bool = True,
        skip_mro: bool = False,
        **config: Any,
    ):
        if skip_mro is True:
            return super().from_config(
                scheduler=scheduler,
                instance=instance,
                url=url,
                **config,
            )
        elif url is None and instance in cls.CLOUD_INSTANCES:
            return BitbucketCloudLister.from_config(
                scheduler=scheduler,
                instance=instance,
                url=url,
                incremental=incremental,
                skip_mro=True,
                **config,
            )
        else:
            return BitbucketServerLister.from_config(
                scheduler=scheduler,
                instance=instance,
                url=url,
                skip_mro=True,
                **config,
            )


class BitbucketServerLister(
    BitbucketLister,
    StatelessLister[Repositories],
):
    """List origins from Bitbucket Server and Data Centre instances using the REST API.
    https://docs.atlassian.com/bitbucket-server/rest/7.0.0/bitbucket-rest.html#idp392
    https://developer.atlassian.com/server/bitbucket/rest/v1000/api-group-repository/#api-api-latest-repos-get
    """

    URL_PARAMS = {}
    THIS_PAGE = "start"
    LEN_PAGE = "limit"
    NEXT_PAGE = "nextPageStart"
    SCM = "scmId"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: Optional[str] = None,
        instance: Optional[str] = None,
        credentials: CredentialsType = None,
        max_origins_per_page: Optional[int] = None,
        max_pages: Optional[int] = None,
        enable_origins: bool = True,
        **kwargs,
    ):
        super().__init__(
            scheduler=scheduler,
            credentials=credentials,
            url=url,
            instance=instance,
            max_origins_per_page=max_origins_per_page,
            max_pages=max_pages,
            enable_origins=enable_origins,
            **kwargs,
        )

        self.url = self.url.rstrip("/") + "/"

        self.api_url = self.url + "rest/api/1.0/repos"

    def page_url(self, page: Optional[int] = None) -> Optional[str]:
        if page is not None:
            this_page = page * self.url_params[self.LEN_PAGE]
            extra_url_params = {self.THIS_PAGE: this_page}
        else:
            extra_url_params = {}
        params = self.url_params | extra_url_params
        return f"{self.api_url}?{parse.urlencode(params)}"

    def initial_page(self) -> int:
        return 0

    def next_page(self, body: Page) -> Any:
        return body.get(self.NEXT_PAGE)

    def error_url_params(self, body: Page, page: int):
        return {
            self.LEN_PAGE: body.get(self.LEN_PAGE),
            "fields": self.NEXT_PAGE,
            self.THIS_PAGE: page,
        }

    def get_last_update(self, repo: Repository):
        return None

    def get_enabled(self, repo: Repository) -> bool:
        return repo.get("public", True)


@dataclass
class BitbucketCloudListerState:
    """State of Bitbucket Cloud lister"""

    last_repo_cdate: Optional[datetime] = None
    """Creation date and time of the last listed repository during an
    incremental pass"""


class BitbucketCloudLister(
    BitbucketLister,
    Lister[BitbucketCloudListerState, Repositories],
):
    """List origins from Bitbucket Cloud using the REST API.

    https://developer.atlassian.com/cloud/bitbucket/rest/api-group-repositories/#api-repositories-get

    Bitbucket Cloud API has the following rate-limit configuration:

      * 60 requests per hour for anonymous users

      * 1000 requests per hour for authenticated users

    The lister is working in anonymous mode by default but Bitbucket account
    credentials can be provided to perform authenticated requests.
    """

    URL_PARAMS = {
        # only return needed JSON fields in bitbucket API responses
        # (also prevent errors 500 when listing)
        "fields": (
            "next,"
            "values.is_private,"
            "values.scm,"
            "values.links.clone,"
            "values.updated_on,"
            "values.created_on,"
        )
    }
    THIS_PAGE = "after"
    LEN_PAGE = "pagelen"
    NEXT_PAGE = "next"
    SCM = "scm"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: Optional[str] = None,
        instance: Optional[str] = None,
        credentials: CredentialsType = None,
        max_origins_per_page: Optional[int] = None,
        max_pages: Optional[int] = None,
        enable_origins: bool = True,
        incremental: bool = True,
        **kwargs,
    ):
        if url is None and (not instance or instance == "bitbucket"):
            instance = "bitbucket.org"

        super().__init__(
            scheduler=scheduler,
            credentials=credentials,
            url=url,
            instance=instance,
            max_origins_per_page=max_origins_per_page,
            max_pages=max_pages,
            enable_origins=enable_origins,
            **kwargs,
        )

        self.url = self.url.rstrip("/") + "/"

        # Calculate the API URL in a way that would also work with
        # imaginary non-bitbucket.org Bitbucket Cloud instances.
        api_url = parse.urlparse(self.url)
        api_url = api_url._replace(netloc="api." + api_url.netloc)
        api_url = api_url._replace(path=api_url.path + "2.0/repositories")
        self.api_url = parse.urlunparse(api_url)

        self.incremental = incremental

    def state_from_dict(self, d: BackendStateType) -> BitbucketCloudListerState:
        last_repo_cdate = d.get("last_repo_cdate")
        if last_repo_cdate is not None:
            d["last_repo_cdate"] = iso8601.parse_date(last_repo_cdate)
        return BitbucketCloudListerState(**d)

    def state_to_dict(self, state: BitbucketCloudListerState) -> BackendStateType:
        d = asdict(state)
        last_repo_cdate = d.get("last_repo_cdate")
        if last_repo_cdate is not None:
            d["last_repo_cdate"] = last_repo_cdate.isoformat()
        return d

    def page_url(self, page: Optional[int] = None) -> Optional[str]:
        return None

    def initial_page(self) -> str:
        last_repo_cdate: str = "1970-01-01"
        if (
            self.incremental
            and self.state is not None
            and self.state.last_repo_cdate is not None
        ):
            last_repo_cdate = self.state.last_repo_cdate.isoformat()
        return last_repo_cdate

    def next_page(self, body: Page) -> Optional[str]:
        next_page_url = body.get(self.NEXT_PAGE)
        if next_page_url is not None:
            next_page_url = parse.urlparse(next_page_url)
            if not next_page_url.query:
                logger.warning("Failed to parse url %s", next_page_url)
                return None
            return parse.parse_qs(next_page_url.query)[self.THIS_PAGE][0]
        else:
            # last page
            return None

    def error_url_params(self, body: Page, page: str) -> Dict[str, Any]:
        return {
            self.LEN_PAGE: self.url_params[self.LEN_PAGE],
            "fields": self.NEXT_PAGE,
            self.THIS_PAGE: page,
        }

    def get_last_update(self, repo: Repository):
        return iso8601.parse_date(repo["updated_on"])

    def get_enabled(self, repo: Repository) -> bool:
        return not repo.get("is_private", False)

    def commit_page(self, page: Repositories) -> None:
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
