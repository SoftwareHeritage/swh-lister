# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json
import logging
from pathlib import Path
import subprocess
from typing import Any, Dict, Iterator, List
from urllib.parse import urlparse

import iso8601

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, StatelessLister

logger = logging.getLogger(__name__)

# Aliasing the page results returned by `get_pages` method from the lister.
CratesListerPage = List[Dict[str, Any]]


class CratesLister(StatelessLister[CratesListerPage]):
    """List origins from the "crates.io" forge.

    It basically fetches https://github.com/rust-lang/crates.io-index.git to a
    temp directory and then walks through each file to get the crate's info.
    """

    # Part of the lister API, that identifies this lister
    LISTER_NAME = "crates"
    # (Optional) CVS type of the origins listed by this lister, if constant
    VISIT_TYPE = "crates"

    INSTANCE = "crates"
    INDEX_REPOSITORY_URL = "https://github.com/rust-lang/crates.io-index.git"
    DESTINATION_PATH = Path("/tmp/crates.io-index")
    CRATE_FILE_URL_PATTERN = (
        "https://static.crates.io/crates/{crate}/{crate}-{version}.crate"
    )
    CRATE_API_URL_PATTERN = "https://crates.io/api/v1/crates/{crate}"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        credentials: CredentialsType = None,
    ):
        super().__init__(
            scheduler=scheduler,
            credentials=credentials,
            url=self.INDEX_REPOSITORY_URL,
            instance=self.INSTANCE,
        )

    def get_index_repository(self) -> None:
        """Get crates.io-index repository up to date running git command."""

        subprocess.check_call(
            [
                "git",
                "clone",
                self.INDEX_REPOSITORY_URL,
                self.DESTINATION_PATH,
            ]
        )

    def get_crates_index(self) -> List[Path]:
        """Build a sorted list of file paths excluding dotted directories and
        dotted files.

        Each file path corresponds to a crate that lists all available
        versions.
        """

        crates_index = sorted(
            path
            for path in self.DESTINATION_PATH.rglob("*")
            if not any(part.startswith(".") for part in path.parts)
            and path.is_file()
            and path != self.DESTINATION_PATH / "config.json"
        )

        return crates_index

    def get_pages(self) -> Iterator[CratesListerPage]:
        """Yield an iterator sorted by name in ascending order of pages.

        Each page is a list of crate versions with:
            - name: Name of the crate
            - version: Version
            - checksum: Checksum
            - crate_file: Url of the crate file
            - last_update: Date of the last commit of the corresponding index
                file
        """
        # Fetch crates.io index repository
        self.get_index_repository()
        # Get a list of all crates files from the index repository
        crates_index = self.get_crates_index()
        logger.debug("found %s crates in crates_index", len(crates_index))

        for crate in crates_index:
            page = []
            # %cI is for strict iso8601 date formatting
            last_update_str = subprocess.check_output(
                ["git", "log", "-1", "--pretty=format:%cI", str(crate)],
                cwd=self.DESTINATION_PATH,
            )
            last_update = iso8601.parse_date(last_update_str.decode().strip())

            with crate.open("rb") as current_file:
                for line in current_file:
                    data = json.loads(line)
                    # pick only the data we need
                    page.append(
                        dict(
                            name=data["name"],
                            version=data["vers"],
                            checksum=data["cksum"],
                            crate_file=self.CRATE_FILE_URL_PATTERN.format(
                                crate=data["name"], version=data["vers"]
                            ),
                            last_update=last_update,
                        )
                    )
            yield page

    def get_origins_from_page(self, page: CratesListerPage) -> Iterator[ListedOrigin]:
        """Iterate on all crate pages and yield ListedOrigin instances."""

        assert self.lister_obj.id is not None

        url = self.CRATE_API_URL_PATTERN.format(crate=page[0]["name"])
        last_update = page[0]["last_update"]
        artifacts = []

        for version in page:
            filename = urlparse(version["crate_file"]).path.split("/")[-1]
            # Build an artifact entry following original-artifacts-json specification
            # https://docs.softwareheritage.org/devel/swh-storage/extrinsic-metadata-specification.html#original-artifacts-json  # noqa: B950
            artifact = {
                "filename": f"{filename}",
                "checksums": {
                    "sha256": f"{version['checksum']}",
                },
                "url": version["crate_file"],
                "version": version["version"],
            }
            artifacts.append(artifact)

        yield ListedOrigin(
            lister_id=self.lister_obj.id,
            visit_type=self.VISIT_TYPE,
            url=url,
            last_update=last_update,
            extra_loader_arguments={
                "artifacts": artifacts,
            },
        )
