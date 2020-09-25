# Copyright (C) 2017-2019 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import bz2
from collections import defaultdict
import datetime
import gzip
import logging
import lzma
from typing import Any, Dict, Mapping, Optional

from debian.deb822 import Sources
from requests import Response
from sqlalchemy.orm import joinedload, load_only
from sqlalchemy.schema import CreateTable, DropTable

from swh.lister.core.lister_base import FetchError, ListerBase
from swh.lister.core.lister_transports import ListerHttpTransport
from swh.lister.debian.models import (
    AreaSnapshot,
    Distribution,
    DistributionSnapshot,
    Package,
    TempPackage,
)

decompressors = {
    "gz": lambda f: gzip.GzipFile(fileobj=f),
    "bz2": bz2.BZ2File,
    "xz": lzma.LZMAFile,
}


logger = logging.getLogger(__name__)


class DebianLister(ListerHttpTransport, ListerBase):
    MODEL = Package
    PATH_TEMPLATE = None
    LISTER_NAME = "debian"
    instance = "debian"

    def __init__(
        self,
        distribution: str = "Debian",
        date: Optional[datetime.datetime] = None,
        override_config: Mapping = {},
    ):
        """Initialize the debian lister for a given distribution at a given
        date.

        Args:
            distribution: name of the distribution (e.g. "Debian")
            date: date the snapshot is taken (defaults to now if empty)
            override_config: Override configuration (which takes precedence
               over the parameters if provided)

        """
        ListerHttpTransport.__init__(self, url="notused")
        ListerBase.__init__(self, override_config=override_config)
        self.distribution = override_config.get("distribution", distribution)
        self.date = override_config.get("date", date) or datetime.datetime.now(
            tz=datetime.timezone.utc
        )

    def transport_request(self, identifier) -> Response:
        """Subvert ListerHttpTransport.transport_request, to try several
        index URIs in turn.

        The Debian repository format supports several compression algorithms
        across the ages, so we try several URIs.

        Once we have found a working URI, we break and set `self.decompressor`
        to the one that matched.

        Returns:
            a requests Response object.

        Raises:
            FetchError: when all the URIs failed to be retrieved.
        """
        response = None
        compression = None

        for uri, compression in self.area.index_uris():
            response = super().transport_request(uri)
            if response.status_code == 200:
                break
        else:
            raise FetchError("Could not retrieve index for %s" % self.area)
        self.decompressor = decompressors.get(compression)
        return response

    def request_uri(self, identifier):
        # In the overridden transport_request, we pass
        # ListerBase.transport_request() the full URI as identifier, so we
        # need to return it here.
        return identifier

    def request_params(self, identifier) -> Dict[str, Any]:
        # Enable streaming to allow wrapping the response in the decompressor
        # in transport_response_simplified.
        params = super().request_params(identifier)
        params["stream"] = True
        return params

    def transport_response_simplified(self, response):
        """Decompress and parse the package index fetched in `transport_request`.

        For each package, we "pivot" the file list entries (Files,
        Checksums-Sha1, Checksums-Sha256), to return a files dict mapping
        filenames to their checksums.
        """
        if self.decompressor:
            data = self.decompressor(response.raw)
        else:
            data = response.raw

        for src_pkg in Sources.iter_paragraphs(data.readlines()):
            files = defaultdict(dict)

            for field in src_pkg._multivalued_fields:
                if field.startswith("checksums-"):
                    sum_name = field[len("checksums-") :]
                else:
                    sum_name = "md5sum"
                if field in src_pkg:
                    for entry in src_pkg[field]:
                        name = entry["name"]
                        files[name]["name"] = entry["name"]
                        files[name]["size"] = int(entry["size"], 10)
                        files[name][sum_name] = entry[sum_name]

            yield {
                "name": src_pkg["Package"],
                "version": src_pkg["Version"],
                "directory": src_pkg["Directory"],
                "files": files,
            }

    def inject_repo_data_into_db(self, models_list):
        """Generate the Package entries that didn't previously exist.

        Contrary to ListerBase, we don't actually insert the data in
        database. `schedule_missing_tasks` does it once we have the
        origin and task identifiers.
        """
        by_name_version = {}
        temp_packages = []

        area_id = self.area.id

        for model in models_list:
            name = model["name"]
            version = model["version"]
            temp_packages.append(
                {"area_id": area_id, "name": name, "version": version,}
            )
            by_name_version[name, version] = model

        # Add all the listed packages to a temporary table
        self.db_session.execute(CreateTable(TempPackage.__table__))
        self.db_session.bulk_insert_mappings(TempPackage, temp_packages)

        def exists_tmp_pkg(db_session, model):
            return (
                db_session.query(model)
                .filter(Package.area_id == TempPackage.area_id)
                .filter(Package.name == TempPackage.name)
                .filter(Package.version == TempPackage.version)
                .exists()
            )

        # Filter out the packages that already exist in the main Package table
        new_packages = (
            self.db_session.query(TempPackage)
            .options(load_only("name", "version"))
            .filter(~exists_tmp_pkg(self.db_session, Package))
            .all()
        )

        self.old_area_packages = (
            self.db_session.query(Package)
            .filter(exists_tmp_pkg(self.db_session, TempPackage))
            .all()
        )

        self.db_session.execute(DropTable(TempPackage.__table__))

        added_packages = []
        for package in new_packages:
            model = by_name_version[package.name, package.version]

            added_packages.append(Package(area=self.area, **model))

        self.db_session.add_all(added_packages)
        return added_packages

    def schedule_missing_tasks(self, models_list, added_packages):
        """We create tasks at the end of the full snapshot processing"""
        return

    def create_tasks_for_snapshot(self, snapshot):
        tasks = [
            snapshot.task_for_package(name, versions)
            for name, versions in snapshot.get_packages().items()
        ]

        return self.scheduler.create_tasks(tasks)

    def run(self):
        """Run the lister for a given (distribution, area) tuple.

        """
        distribution = (
            self.db_session.query(Distribution)
            .options(joinedload(Distribution.areas))
            .filter(Distribution.name == self.distribution)
            .one_or_none()
        )

        if not distribution:
            logger.error("Distribution %s is not registered" % self.distribution)
            return {"status": "failed"}

        if not distribution.type == "deb":
            logger.error("Distribution %s is not a Debian derivative" % distribution)
            return {"status": "failed"}

        date = self.date

        logger.debug(
            "Creating snapshot for distribution %s on date %s" % (distribution, date)
        )

        snapshot = DistributionSnapshot(date=date, distribution=distribution)

        self.db_session.add(snapshot)

        for area in distribution.areas:
            if not area.active:
                continue

            self.area = area

            logger.debug("Processing area %s" % area)

            _, new_area_packages = self.ingest_data(None)
            area_snapshot = AreaSnapshot(snapshot=snapshot, area=area)
            self.db_session.add(area_snapshot)
            area_snapshot.packages.extend(new_area_packages)
            area_snapshot.packages.extend(self.old_area_packages)

        self.create_tasks_for_snapshot(snapshot)

        self.db_session.commit()

        return {"status": "eventful"}
