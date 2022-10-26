# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from datetime import datetime
import logging
from typing import Any, Dict, Iterator, List, Optional
from urllib.parse import urljoin

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, StatelessLister

logger = logging.getLogger(__name__)

# Aliasing the page results returned by `get_pages` method from the lister.
PuppetListerPage = List[Dict[str, Any]]


class PuppetLister(StatelessLister[PuppetListerPage]):
    """The Puppet lister list origins from 'Puppet Forge'"""

    LISTER_NAME = "puppet"
    VISIT_TYPE = "puppet"
    INSTANCE = "puppet"

    BASE_URL = "https://forgeapi.puppet.com/"

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

    def get_pages(self) -> Iterator[PuppetListerPage]:
        """Yield an iterator which returns 'page'

        It request the http api endpoint to get a paginated results of modules,
        and retrieve a `next` url. It ends when `next` json value is `null`.

        Open Api specification for getModules endpoint:
        https://forgeapi.puppet.com/#tag/Module-Operations/operation/getModules

        """
        # limit = 100 is the max value for pagination
        limit: int = 100
        response = self.http_request(
            f"{self.BASE_URL}v3/modules", params={"limit": limit}
        )
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
