# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging
from typing import Any, Dict, Iterator, List, Optional

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, StatelessLister

logger = logging.getLogger(__name__)

# Aliasing the page results returned by `get_pages` method from the lister.
CpanListerPage = List[Dict[str, Any]]


class CpanLister(StatelessLister[CpanListerPage]):
    """The Cpan lister list origins from 'Cpan', the Comprehensive Perl Archive
    Network."""

    LISTER_NAME = "cpan"
    VISIT_TYPE = "cpan"
    INSTANCE = "cpan"

    BASE_URL = "https://fastapi.metacpan.org/v1/"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        credentials: Optional[CredentialsType] = None,
    ):
        super().__init__(
            scheduler=scheduler,
            credentials=credentials,
            instance=self.INSTANCE,
            url=self.BASE_URL,
        )

    def get_pages(self) -> Iterator[CpanListerPage]:
        """Yield an iterator which returns 'page'"""

        endpoint = f"{self.BASE_URL}distribution/_search"
        scrollendpoint = f"{self.BASE_URL}_search/scroll"
        size: int = 1000

        res = self.http_request(
            endpoint,
            params={
                "fields": ["name"],
                "size": size,
                "scroll": "1m",
            },
        )
        data = res.json()["hits"]["hits"]
        yield data

        _scroll_id = res.json()["_scroll_id"]

        while data:
            scroll_res = self.http_request(
                scrollendpoint, params={"scroll": "1m", "scroll_id": _scroll_id}
            )
            data = scroll_res.json()["hits"]["hits"]
            _scroll_id = scroll_res.json()["_scroll_id"]
            yield data

    def get_origins_from_page(self, page: CpanListerPage) -> Iterator[ListedOrigin]:
        """Iterate on all pages and yield ListedOrigin instances."""
        assert self.lister_obj.id is not None

        for entry in page:
            # Skip the entry if 'fields' or 'name' keys are missing
            if "fields" not in entry or "name" not in entry["fields"]:
                continue

            pkgname = entry["fields"]["name"]
            # TODO: Check why sometimes its a one value list
            if type(pkgname) != str:
                pkgname = pkgname[0]

            url = f"https://metacpan.org/dist/{pkgname}"

            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                visit_type=self.VISIT_TYPE,
                url=url,
                last_update=None,
            )
