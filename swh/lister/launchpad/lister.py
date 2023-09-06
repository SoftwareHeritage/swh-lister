# Copyright (C) 2020-2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any, Dict, Iterator, Optional, Tuple

import iso8601
from launchpadlib.launchpad import Launchpad
from lazr.restfulclient.errors import RestfulError
from lazr.restfulclient.resource import Collection
from tenacity.before_sleep import before_sleep_log

from swh.core.retry import http_retry, retry_if_exception
from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, Lister

logger = logging.getLogger(__name__)

VcsType = str
LaunchpadPageType = Tuple[VcsType, Collection]


SUPPORTED_VCS_TYPES = ("git", "bzr")


@dataclass
class LaunchpadListerState:
    """State of Launchpad lister"""

    git_date_last_modified: Optional[datetime] = None
    """modification date of last updated git repository since last listing"""
    bzr_date_last_modified: Optional[datetime] = None
    """modification date of last updated bzr repository since last listing"""


def origin(vcs_type: str, repo: Any) -> str:
    """Determine the origin url out of a repository with a given vcs_type"""
    return repo.git_https_url if vcs_type == "git" else repo.web_link


def retry_if_restful_error(retry_state):
    return retry_if_exception(retry_state, lambda e: isinstance(e, RestfulError))


class LaunchpadLister(Lister[LaunchpadListerState, LaunchpadPageType]):
    """
    List repositories from Launchpad (git or bzr).

    Args:
        scheduler: instance of SchedulerInterface
        incremental: defines if incremental listing should be used, in that case
            only modified or new repositories since last incremental listing operation
            will be returned
    """

    LAUNCHPAD_URL = "https://launchpad.net/"
    LISTER_NAME = "launchpad"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: str = LAUNCHPAD_URL,
        instance: str = LISTER_NAME,
        incremental: bool = False,
        credentials: CredentialsType = None,
        max_origins_per_page: Optional[int] = None,
        max_pages: Optional[int] = None,
        enable_origins: bool = True,
    ):
        super().__init__(
            scheduler=scheduler,
            url=url,
            instance=instance,
            credentials=credentials,
            max_origins_per_page=max_origins_per_page,
            max_pages=max_pages,
            enable_origins=enable_origins,
        )
        self.incremental = incremental
        self.date_last_modified: Dict[str, Optional[datetime]] = {
            "git": None,
            "bzr": None,
        }

    def state_from_dict(self, d: Dict[str, Any]) -> LaunchpadListerState:
        for vcs_type in SUPPORTED_VCS_TYPES:
            key = f"{vcs_type}_date_last_modified"
            date_last_modified = d.get(key)
            if date_last_modified is not None:
                d[key] = iso8601.parse_date(date_last_modified)

        return LaunchpadListerState(**d)

    def state_to_dict(self, state: LaunchpadListerState) -> Dict[str, Any]:
        d: Dict[str, Optional[str]] = {}
        for vcs_type in SUPPORTED_VCS_TYPES:
            attribute_name = f"{vcs_type}_date_last_modified"
            d[attribute_name] = None

            if hasattr(state, attribute_name):
                date_last_modified = getattr(state, attribute_name)
                if date_last_modified is not None:
                    d[attribute_name] = date_last_modified.isoformat()
        return d

    @http_retry(
        retry=retry_if_restful_error,
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _page_request(
        self, launchpad, vcs_type: str, date_last_modified: Optional[datetime]
    ) -> Optional[Collection]:
        """Querying the page of results for a given vcs_type since the date_last_modified. If
        some issues occurs, this will deal with the retrying policy.

        """
        get_vcs_fns = {
            "git": launchpad.git_repositories.getRepositories,
            "bzr": launchpad.branches.getBranches,
        }

        return get_vcs_fns[vcs_type](
            order_by="most neglected first",
            modified_since_date=date_last_modified,
        )

    def get_pages(self) -> Iterator[LaunchpadPageType]:
        """
        Yields an iterator on all git/bzr repositories hosted on Launchpad sorted
        by last modification date in ascending order.
        """
        launchpad = Launchpad.login_anonymously(
            "softwareheritage", "production", version="devel"
        )
        if self.incremental:
            self.date_last_modified = {
                "git": self.state.git_date_last_modified,
                "bzr": self.state.bzr_date_last_modified,
            }
        for vcs_type in SUPPORTED_VCS_TYPES:
            try:
                result = self._page_request(
                    launchpad, vcs_type, self.date_last_modified[vcs_type]
                )
            except RestfulError as e:
                logger.warning("Listing %s origins raised %s", vcs_type, e)
                result = None
            if not result:
                continue
            yield vcs_type, result

    def get_origins_from_page(self, page: LaunchpadPageType) -> Iterator[ListedOrigin]:
        """
        Iterate on all git repositories and yield ListedOrigin instances.
        """
        assert self.lister_obj.id is not None

        vcs_type, repos = page

        try:
            for repo in repos:
                origin_url = origin(vcs_type, repo)

                # filter out origins with invalid URL
                if not origin_url.startswith("https://"):
                    continue

                last_update = repo.date_last_modified

                self.date_last_modified[vcs_type] = last_update

                logger.debug(
                    "Found origin %s with type %s last updated on %s",
                    origin_url,
                    vcs_type,
                    last_update,
                )

                yield ListedOrigin(
                    lister_id=self.lister_obj.id,
                    visit_type=vcs_type,
                    url=origin_url,
                    last_update=last_update,
                )
        except RestfulError as e:
            logger.warning("Listing %s origins raised %s", vcs_type, e)

    def finalize(self) -> None:
        git_date_last_modified = self.date_last_modified["git"]
        bzr_date_last_modified = self.date_last_modified["bzr"]
        if git_date_last_modified is None and bzr_date_last_modified is None:
            return

        if self.incremental and (
            self.state.git_date_last_modified is None
            or (
                git_date_last_modified is not None
                and git_date_last_modified > self.state.git_date_last_modified
            )
        ):
            self.state.git_date_last_modified = git_date_last_modified

        if self.incremental and (
            self.state.bzr_date_last_modified is None
            or (
                bzr_date_last_modified is not None
                and bzr_date_last_modified > self.state.bzr_date_last_modified
            )
        ):
            self.state.bzr_date_last_modified = self.date_last_modified["bzr"]

        self.updated = True
