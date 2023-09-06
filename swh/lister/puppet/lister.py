# Copyright (C) 2022-2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Dict, Iterator, List, Optional
from urllib.parse import urljoin

import iso8601

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, Lister

logger = logging.getLogger(__name__)

# Aliasing the page results returned by `get_pages` method from the lister.
PuppetListerPage = List[Dict[str, Any]]


@dataclass
class PuppetListerState:
    """Store lister state for incremental mode operations"""

    last_listing_date: Optional[datetime] = None
    """Last date when Puppet lister was executed"""


class PuppetLister(Lister[PuppetListerState, PuppetListerPage]):
    """The Puppet lister list origins from 'Puppet Forge'"""

    LISTER_NAME = "puppet"
    VISIT_TYPE = "puppet"
    INSTANCE = "puppet"

    BASE_URL = "https://forgeapi.puppet.com/"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: str = BASE_URL,
        instance: str = INSTANCE,
        credentials: Optional[CredentialsType] = None,
        max_origins_per_page: Optional[int] = None,
        max_pages: Optional[int] = None,
        enable_origins: bool = True,
    ):
        super().__init__(
            scheduler=scheduler,
            credentials=credentials,
            instance=instance,
            url=url,
            max_origins_per_page=max_origins_per_page,
            max_pages=max_pages,
            enable_origins=enable_origins,
        )
        # Store the datetime the lister runs for incremental purpose
        self.listing_date = datetime.now()

    def state_from_dict(self, d: Dict[str, Any]) -> PuppetListerState:
        last_listing_date = d.get("last_listing_date")
        if last_listing_date is not None:
            d["last_listing_date"] = iso8601.parse_date(last_listing_date)
        return PuppetListerState(**d)

    def state_to_dict(self, state: PuppetListerState) -> Dict[str, Any]:
        d: Dict[str, Optional[str]] = {"last_listing_date": None}
        last_listing_date = state.last_listing_date
        if last_listing_date is not None:
            d["last_listing_date"] = last_listing_date.isoformat()
        return d

    def get_pages(self) -> Iterator[PuppetListerPage]:
        """Yield an iterator which returns 'page'

        It request the http api endpoint to get a paginated results of modules,
        and retrieve a `next` url. It ends when `next` json value is `null`.

        Open Api specification for getModules endpoint:
        https://forgeapi.puppet.com/#tag/Module-Operations/operation/getModules

        """
        # limit = 100 is the max value for pagination
        limit: int = 100
        params: Dict[str, Any] = {"limit": limit}

        if self.state.last_listing_date:
            # Incremental mode filter query
            # To ensure we don't miss records between two lister runs `last_str`` must be
            # set with an offset of -15 hours, which is the lower timezone recorded in the
            # tzdb
            last_str = (
                self.state.last_listing_date.astimezone(timezone(timedelta(hours=-15)))
                .date()
                .isoformat()
            )
            params["with_release_since"] = last_str

        response = self.http_request(f"{self.BASE_URL}v3/modules", params=params)
        data: Dict[str, Any] = response.json()
        yield data["results"]

        while data["pagination"]["next"]:
            response = self.http_request(
                urljoin(self.BASE_URL, data["pagination"]["next"])
            )
            data = response.json()
            yield data["results"]

    def get_origins_from_page(self, page: PuppetListerPage) -> Iterator[ListedOrigin]:
        """Iterate on all pages and yield ListedOrigin instances."""
        assert self.lister_obj.id is not None

        dt_parse_pattern = "%Y-%m-%d %H:%M:%S %z"

        for entry in page:
            last_update = datetime.strptime(entry["updated_at"], dt_parse_pattern)
            pkgname = entry["name"]
            owner = entry["owner"]["slug"]
            url = f"https://forge.puppet.com/modules/{owner}/{pkgname}"
            artifacts = []
            for release in entry["releases"]:
                # Build an artifact entry following original-artifacts-json specification
                # https://docs.softwareheritage.org/devel/swh-storage/extrinsic-metadata-specification.html#original-artifacts-json  # noqa: B950
                checksums = {}

                if release["version"] == entry["current_release"]["version"]:
                    # checksums are only available for current release
                    for checksum in ("md5", "sha256"):
                        checksums[checksum] = entry["current_release"][
                            f"file_{checksum}"
                        ]
                else:
                    # use file length as basic content check instead
                    checksums["length"] = release["file_size"]

                artifacts.append(
                    {
                        "filename": release["file_uri"].split("/")[-1],
                        "url": urljoin(self.BASE_URL, release["file_uri"]),
                        "version": release["version"],
                        "last_update": datetime.strptime(
                            release["created_at"], dt_parse_pattern
                        ).isoformat(),
                        "checksums": checksums,
                    }
                )

            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                visit_type=self.VISIT_TYPE,
                url=url,
                last_update=last_update,
                extra_loader_arguments={"artifacts": artifacts},
            )

    def finalize(self) -> None:
        self.state.last_listing_date = self.listing_date
        self.updated = True
