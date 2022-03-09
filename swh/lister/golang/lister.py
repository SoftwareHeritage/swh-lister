# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from datetime import datetime
import json
import logging
from typing import Any, Dict, Iterator, List, Optional, Tuple

import iso8601
import requests
from tenacity import before_sleep_log

from swh.lister.utils import retry_policy_generic, throttling_retry
from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from .. import USER_AGENT
from ..pattern import CredentialsType, StatelessLister

logger = logging.getLogger(__name__)

GolangPageType = List[Dict[str, Any]]


class GolangLister(StatelessLister[GolangPageType]):
    """
    List all Golang modules and send associated origins to scheduler.

    The lister queries the Golang module index, whose documentation can be found
    at https://index.golang.org
    """

    GOLANG_MODULES_INDEX_URL = "https://index.golang.org/index"
    # `limit` seems to be... limited to 2000.
    GOLANG_MODULES_INDEX_LIMIT = 2000
    LISTER_NAME = "Golang"

    def __init__(
        self, scheduler: SchedulerInterface, credentials: CredentialsType = None,
    ):
        super().__init__(
            scheduler=scheduler,
            url=self.GOLANG_MODULES_INDEX_URL,
            instance="Golang",
            credentials=credentials,
        )

        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/json", "User-Agent": USER_AGENT}
        )

    @throttling_retry(
        retry=retry_policy_generic,
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def api_request(self, url: str) -> List[str]:
        logger.debug("Fetching URL %s", url)

        response = self.session.get(url)

        if response.status_code not in (200, 304):
            # Log response content to ease debugging
            logger.warning(
                "Unexpected HTTP status code %s for URL %s",
                response.status_code,
                response.url,
            )

        response.raise_for_status()

        return response.text.split()

    def get_single_page(
        self, since: Optional[datetime] = None
    ) -> Tuple[GolangPageType, Optional[datetime]]:
        """Return a page from the API and the timestamp of its last entry.
        Since all entries are sorted by chronological order, the timestamp is useful
        both for pagination and later for incremental runs."""
        url = f"{self.url}?limit={self.GOLANG_MODULES_INDEX_LIMIT}"
        if since is not None:
            # The Golang index does not understand `+00:00` for some reason
            # and expects the "timezone zero" notation instead. This works
            # because all times are UTC.
            utc_offset = since.utcoffset()
            assert (
                utc_offset is not None and utc_offset.total_seconds() == 0
            ), "Non-UTC datetime"
            as_date = since.isoformat().replace("+00:00", "Z")
            url = f"{url}&since={as_date}"

        entries = self.api_request(url)
        page: GolangPageType = []
        if not entries:
            return page, since

        for as_json in entries:
            entry = json.loads(as_json)
            timestamp = iso8601.parse_date(entry["Timestamp"])
            # We've already parsed it and we'll need the datetime later, save it
            entry["Timestamp"] = timestamp
            page.append(entry)
            # The index is guaranteed to be sorted in chronological order
            since = timestamp

        return page, since

    def get_pages(self) -> Iterator[GolangPageType]:
        page, since = self.get_single_page()
        last_since = since
        while page:
            yield page
            page, since = self.get_single_page(since=since)
            if last_since == since:
                # The index returns packages whose timestamp are greater or
                # equal to the date provided as parameter, which will create
                # an infinite loop if not stopped here.
                return []
            last_since = since

    def get_origins_from_page(self, page: GolangPageType) -> Iterator[ListedOrigin]:
        """
        Iterate on all Golang projects and yield ListedOrigin instances.
        """
        assert self.lister_obj.id is not None

        for module in page:
            path = module["Path"]
            # The loader will be expected to use the golang proxy to do the
            # actual downloading. We're using `pkg.go.dev` so that the URL points
            # to somewhere useful for a human instead of an (incomplete) API path.
            origin_url = f"https://pkg.go.dev/{path}"

            # Since the Go index lists versions and not just packages, there will
            # be duplicates. Fortunately, `ListedOrigins` are "upserted" server-side,
            # so only the last timestamp will be used, with no duplicates.
            # Performance should not be an issue as they are sent to the db in bulk.
            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                url=origin_url,
                visit_type="golang",
                last_update=module["Timestamp"],
            )
