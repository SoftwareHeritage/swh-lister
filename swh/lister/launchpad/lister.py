# Copyright (C) 2020-2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any, Dict, Iterator, Optional

import iso8601
from launchpadlib.launchpad import Launchpad
from lazr.restfulclient.resource import Collection

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, Lister

logger = logging.getLogger(__name__)

LaunchpadPageType = Iterator[Collection]


@dataclass
class LaunchpadListerState:
    """State of Launchpad lister"""

    date_last_modified: Optional[datetime] = None
    """modification date of last updated repository since last listing"""


class LaunchpadLister(Lister[LaunchpadListerState, LaunchpadPageType]):
    """
    List git repositories from Launchpad.

    Args:
        scheduler: instance of SchedulerInterface
        incremental: defines if incremental listing should be used, in that case
            only modified or new repositories since last incremental listing operation
            will be returned
    """

    LISTER_NAME = "launchpad"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        incremental: bool = False,
        credentials: CredentialsType = None,
    ):
        super().__init__(
            scheduler=scheduler,
            url="https://launchpad.net/",
            instance="launchpad",
            credentials=credentials,
        )
        self.incremental = incremental
        self.date_last_modified = None

    def state_from_dict(self, d: Dict[str, Any]) -> LaunchpadListerState:
        date_last_modified = d.get("date_last_modified")
        if date_last_modified is not None:
            d["date_last_modified"] = iso8601.parse_date(date_last_modified)
        return LaunchpadListerState(**d)

    def state_to_dict(self, state: LaunchpadListerState) -> Dict[str, Any]:
        d: Dict[str, Optional[str]] = {"date_last_modified": None}
        date_last_modified = state.date_last_modified
        if date_last_modified is not None:
            d["date_last_modified"] = date_last_modified.isoformat()
        return d

    def get_pages(self) -> Iterator[LaunchpadPageType]:
        """
        Yields an iterator on all git repositories hosted on Launchpad sorted
        by last modification date in ascending order.
        """
        launchpad = Launchpad.login_anonymously(
            "softwareheritage", "production", version="devel"
        )
        date_last_modified = None
        if self.incremental:
            date_last_modified = self.state.date_last_modified
        get_repos = launchpad.git_repositories.getRepositories
        yield get_repos(
            order_by="most neglected first", modified_since_date=date_last_modified
        )

    def get_origins_from_page(self, page: LaunchpadPageType) -> Iterator[ListedOrigin]:
        """
        Iterate on all git repositories and yield ListedOrigin instances.
        """
        assert self.lister_obj.id is not None

        prev_origin_url = None

        for repo in page:

            origin_url = repo.git_https_url

            # filter out origins with invalid URL or origin previously listed
            # (last modified repository will be listed twice by launchpadlib)
            if not origin_url.startswith("https://") or origin_url == prev_origin_url:
                continue

            last_update = repo.date_last_modified

            self.date_last_modified = last_update

            logger.debug("Found origin %s last updated on %s", origin_url, last_update)

            prev_origin_url = origin_url

            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                visit_type="git",
                url=origin_url,
                last_update=last_update,
            )

    def finalize(self) -> None:
        if self.date_last_modified is None:
            return

        if self.incremental and (
            self.state.date_last_modified is None
            or self.date_last_modified > self.state.date_last_modified
        ):
            self.state.date_last_modified = self.date_last_modified

        self.updated = True
