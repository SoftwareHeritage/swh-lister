# Copyright (C) 2026  The Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from dataclasses import dataclass
from datetime import datetime, timezone
import gzip
import json
import logging
from typing import Any, Dict, Iterator, Optional
from urllib.parse import urljoin
import zlib

import iso8601

from swh.lister.pattern import CredentialsType, Lister
from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

logger = logging.getLogger(__name__)

Repositories = Dict[str, Any]


@dataclass
class GrokmirrorListerState:
    """State of Grokmirror lister"""

    last_listing_date: Optional[datetime] = None
    """Last date when Grokmirror lister was executed"""


class GrokmirrorLister(Lister[GrokmirrorListerState, Repositories]):
    """Lister class for Grokmirror instances.

    This lister will retrieve the list of published git repositories
    by retrieving the JSON manifest files published on the server,
    checking the modification dates, decompressing and parsing one.

    The lister checks the URLs /manifest.js.gz /manifest.js /manifest

    https://git.kernel.org/pub/scm/utils/grokmirror/grokmirror.git/about/
    """

    LISTER_NAME = "grokmirror"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: Optional[str] = None,
        instance: Optional[str] = None,
        credentials: Optional[CredentialsType] = None,
        max_origins_per_page: Optional[int] = None,
        max_pages: Optional[int] = None,
        enable_origins: bool = True,
        **kwargs,
    ):
        """Lister class for Grokmirror repositories."""
        super().__init__(
            scheduler=scheduler,
            url=url,
            instance=instance,
            credentials=credentials,
            max_origins_per_page=max_origins_per_page,
            max_pages=max_pages,
            enable_origins=enable_origins,
            **kwargs,
        )
        self.listing_date = datetime.now(tz=timezone.utc)

        self.api_url = urljoin(self.url, "manifest.js.gz")

    def state_from_dict(self, d: Dict[str, Any]) -> GrokmirrorListerState:
        last_listing_date = d.get("last_listing_date")
        if last_listing_date is not None:
            d["last_listing_date"] = iso8601.parse_date(last_listing_date)
        return GrokmirrorListerState(**d)

    def state_to_dict(self, state: GrokmirrorListerState) -> Dict[str, Any]:
        d: Dict[str, Optional[str]] = {"last_listing_date": None}
        last_listing_date = state.last_listing_date
        if last_listing_date is not None:
            d["last_listing_date"] = last_listing_date.isoformat()
        return d

    def get_pages(self) -> Iterator[Repositories]:

        headers = {}

        if self.state.last_listing_date is not None:
            if_modified_since = self.state.last_listing_date.strftime(
                "%a, %d %b %Y %H:%M:%S GMT"
            )
            headers["If-Modified-Since"] = if_modified_since

        response = self.http_request(self.api_url, headers=headers)

        if response.status_code == 404:
            self.api_url = self.api_url.removesuffix(".gz")
            response = self.http_request(self.api_url, headers=headers)

        if response.status_code == 404:
            self.api_url = self.api_url.removesuffix(".js")
            response = self.http_request(self.api_url, headers=headers)

        if response.status_code == 200:
            try:
                json_data = gzip.decompress(response.content).decode("utf-8")
            except (gzip.BadGzipFile, OSError, EOFError, zlib.error):
                json_data = response.text

            repositories = json.loads(json_data)

            yield repositories

        elif response.status_code != 304:
            response.raise_for_status()

    def get_origins_from_page(
        self, repositories: Repositories
    ) -> Iterator[ListedOrigin]:
        """Convert Grokmirror repositories into a list of ListedOrigins."""
        assert self.lister_obj.id is not None

        for repo, meta in repositories.items():

            origin_url = urljoin(self.url, repo)

            kwargs: Dict[str, Any] = {}

            if modified := meta.get("modified"):
                kwargs["last_update"] = datetime.fromtimestamp(
                    modified, tz=timezone.utc
                )

            if reference := meta.get("reference"):

                reference_url = urljoin(self.url, reference)

                kwargs["is_fork"] = bool(reference)
                kwargs["forked_from_url"] = reference_url

            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                url=origin_url,
                visit_type="git",
                **kwargs,
            )

            if reference and reference not in repositories:

                yield ListedOrigin(
                    lister_id=self.lister_obj.id,
                    url=reference_url,
                    visit_type="git",
                )

            for symlink in meta.get("symlinks", []):

                origin_url = urljoin(self.url, symlink)

                yield ListedOrigin(
                    lister_id=self.lister_obj.id,
                    url=origin_url,
                    visit_type="git",
                    **kwargs,
                )

    def finalize(self) -> None:
        self.state.last_listing_date = self.listing_date
