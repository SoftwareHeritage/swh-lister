# Copyright (C) 2022-2024  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import csv
from dataclasses import dataclass
from datetime import datetime
import json
import logging
from pathlib import Path
import tarfile
import tempfile
from typing import Any, Dict, Iterator, List, Optional
from urllib.parse import urlparse

import iso8601
from looseversion import LooseVersion2

from swh.core.utils import grouper
from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, Lister

logger = logging.getLogger(__name__)

# Aliasing the page results returned by `get_pages` method from the lister.
CratesListerPage = List[List[Dict[str, Any]]]


@dataclass
class CratesListerState:
    """Store lister state for incremental mode operations.
    'index_last_update' represents the UTC time the crates.io database dump was
    started
    """

    index_last_update: Optional[datetime] = None


class CratesLister(Lister[CratesListerState, CratesListerPage]):
    """List origins from the "crates.io" forge.

    It downloads a tar.gz archive which contains crates.io database table content as
    csv files which is automatically generated every 24 hours.
    Parsing two csv files we can list all Crates.io package names and their related
    versions.

    In incremental mode, it check each entry comparing their 'last_update' value
    with self.state.index_last_update
    """

    LISTER_NAME = "crates"
    VISIT_TYPE = "crates"
    INSTANCE = "crates"

    BASE_URL = "https://crates.io"
    DB_DUMP_URL = "https://static.crates.io/db-dump.tar.gz"

    CRATE_FILE_URL_PATTERN = (
        "https://static.crates.io/crates/{crate}/{crate}-{version}.crate"
    )
    CRATE_URL_PATTERN = "https://crates.io/crates/{crate}"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: str = BASE_URL,
        instance: str = INSTANCE,
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
        self.index_metadata: Dict[str, str] = {}
        self.all_crates_processed = False

    def state_from_dict(self, d: Dict[str, Any]) -> CratesListerState:
        index_last_update = d.get("index_last_update")
        if index_last_update is not None:
            d["index_last_update"] = iso8601.parse_date(index_last_update)
        return CratesListerState(**d)

    def state_to_dict(self, state: CratesListerState) -> Dict[str, Any]:
        d: Dict[str, Optional[str]] = {"index_last_update": None}
        index_last_update = state.index_last_update
        if index_last_update is not None:
            d["index_last_update"] = index_last_update.isoformat()
        return d

    def is_new(self, dt_str: str):
        """Returns True when dt_str is greater than
        self.state.index_last_update
        """
        dt = iso8601.parse_date(dt_str)
        last = self.state.index_last_update
        return not last or (last is not None and last < dt)

    def get_and_parse_db_dump(self) -> Dict[str, Any]:
        """Download and parse csv files from db_dump_path.

        Returns a dict where each entry corresponds to a package name with its related versions.
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            file_name = self.DB_DUMP_URL.split("/")[-1]
            archive_path = Path(tmpdir) / file_name

            # Download the Db dump
            with self.http_request(self.DB_DUMP_URL, stream=True) as res:
                with open(archive_path, "wb") as out_file:
                    for chunk in res.iter_content(chunk_size=1024):
                        out_file.write(chunk)

            # Extract the Db dump
            db_dump_path = Path(str(archive_path).split(".tar.gz")[0])
            members_to_extract = []
            with tarfile.open(archive_path) as tf:
                for member in tf.getmembers():
                    if member.name.endswith(
                        ("/data/crates.csv", "/data/versions.csv", "/metadata.json")
                    ):
                        members_to_extract.append(member)
                tf.extractall(members=members_to_extract, path=db_dump_path)

            csv.field_size_limit(10000000)

            (crates_csv_path,) = list(db_dump_path.glob("*/data/crates.csv"))
            (versions_csv_path,) = list(db_dump_path.glob("*/data/versions.csv"))
            (index_metadata_json_path,) = list(db_dump_path.rglob("*/metadata.json"))

            with index_metadata_json_path.open("rb") as index_metadata_json:
                self.index_metadata = json.load(index_metadata_json)

            crates: Dict[str, Any] = {}
            with crates_csv_path.open() as crates_fd:
                crates_csv = csv.DictReader(crates_fd)
                for item in crates_csv:
                    if self.is_new(item["updated_at"]):
                        # crate 'id' as key
                        crates[item["id"]] = {
                            "name": item["name"],
                            "updated_at": item["updated_at"],
                            "versions": {},
                        }

            data: Dict[str, Any] = {}
            with versions_csv_path.open() as versions_fd:
                versions_csv = csv.DictReader(versions_fd)
                for version in versions_csv:
                    if version["crate_id"] in crates.keys():
                        crate: Dict[str, Any] = crates[version["crate_id"]]
                        crate["versions"][version["num"]] = version
                        # crate 'name' as key
                        data[crate["name"]] = crate
            return data

    def page_entry_dict(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Transform package version definition dict to a suitable
        page entry dict
        """
        crate_file = self.CRATE_FILE_URL_PATTERN.format(
            crate=entry["name"], version=entry["version"]
        )
        filename = urlparse(crate_file).path.split("/")[-1]
        return dict(
            name=entry["name"],
            version=entry["version"],
            checksum=entry["checksum"],
            yanked=True if entry["yanked"] == "t" else False,
            crate_file=crate_file,
            filename=filename,
            last_update=entry["updated_at"],
        )

    def get_pages(self) -> Iterator[CratesListerPage]:
        """Each page is a list of crate versions with:
        - name: Name of the crate
        - version: Version
        - checksum: Checksum
        - yanked: Whether the package is yanked or not
        - crate_file: Url of the crate file
        - filename: File name of the crate file
        - last_update: Last update for that version
        """

        # Fetch crates.io Db dump, then Parse the data.
        dataset = self.get_and_parse_db_dump()

        logger.debug("Found %s crates in crates_index", len(dataset))

        # a page contains up to 1000 crates with versions info
        for crates in grouper(dataset.items(), 1000):
            page = []
            for name, item in crates:
                crate_versions = []
                # sort crate versions
                versions = sorted(item["versions"].keys(), key=LooseVersion2)

                for version in versions:
                    v = item["versions"][version]
                    v["name"] = name
                    v["version"] = version
                    crate_versions.append(self.page_entry_dict(v))

                page.append(crate_versions)

            yield page
        self.all_crates_processed = True

    def get_origins_from_page(self, page: CratesListerPage) -> Iterator[ListedOrigin]:
        """Iterate on all crate pages and yield ListedOrigin instances."""
        assert self.lister_obj.id is not None

        for crate_versions in page:
            url = self.CRATE_URL_PATTERN.format(crate=crate_versions[0]["name"])
            last_update = crate_versions[0]["last_update"]

            artifacts = []

            for entry in crate_versions:
                # Build an artifact entry following original-artifacts-json specification
                # https://docs.softwareheritage.org/devel/swh-storage/extrinsic-metadata-specification.html#original-artifacts-json  # noqa: B950
                artifacts.append(
                    {
                        "version": entry["version"],
                        "filename": entry["filename"],
                        "url": entry["crate_file"],
                        "checksums": {
                            "sha256": entry["checksum"],
                        },
                    }
                )

            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                visit_type=self.VISIT_TYPE,
                url=url,
                last_update=iso8601.parse_date(last_update),
                extra_loader_arguments={
                    "artifacts": artifacts,
                },
            )

    def finalize(self) -> None:
        if not self.state.index_last_update and self.all_crates_processed:
            last = iso8601.parse_date(self.index_metadata["timestamp"])
            self.state.index_last_update = last
            self.updated = True
