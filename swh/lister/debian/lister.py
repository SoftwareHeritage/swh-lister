# Copyright (C) 2017 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import bz2
from collections import defaultdict
import datetime
import gzip
import lzma
import logging

from debian.deb822 import Sources
from sqlalchemy.orm import joinedload, load_only
from sqlalchemy.schema import CreateTable, DropTable

from swh.storage.schemata.distribution import (
    AreaSnapshot, Distribution, DistributionSnapshot, Package,
    TempPackage,
)

from swh.lister.core.lister_base import SWHListerBase, FetchError
from swh.lister.core.lister_transports import SWHListerHttpTransport

decompressors = {
    'gz': lambda f: gzip.GzipFile(fileobj=f),
    'bz2': bz2.BZ2File,
    'xz': lzma.LZMAFile,
}


class DebianLister(SWHListerHttpTransport, SWHListerBase):
    MODEL = Package
    PATH_TEMPLATE = None
    LISTER_NAME = 'debian'

    def __init__(self, override_config=None):
        SWHListerHttpTransport.__init__(self, api_baseurl="bogus")
        SWHListerBase.__init__(self, override_config=override_config)

    def transport_request(self, identifier):
        """Subvert SWHListerHttpTransport.transport_request, to try several
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
            raise FetchError(
                "Could not retrieve index for %s" % self.area
            )
        self.decompressor = decompressors.get(compression)
        return response

    def request_uri(self, identifier):
        # In the overridden transport_request, we pass
        # SWHListerBase.transport_request() the full URI as identifier, so we
        # need to return it here.
        return identifier

    def request_params(self, identifier):
        # Enable streaming to allow wrapping the response in the decompressor
        # in transport_response_simplified.
        params = super().request_params(identifier)
        params['stream'] = True
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
                if field.startswith('checksums-'):
                    sum_name = field[len('checksums-'):]
                else:
                    sum_name = 'md5sum'
                if field in src_pkg:
                    for entry in src_pkg[field]:
                        name = entry['name']
                        files[name]['name'] = entry['name']
                        files[name]['size'] = int(entry['size'], 10)
                        files[name][sum_name] = entry[sum_name]

            yield {
                'name': src_pkg['Package'],
                'version': src_pkg['Version'],
                'directory': src_pkg['Directory'],
                'files': files,
            }

    def inject_repo_data_into_db(self, models_list):
        """Generate the Package entries that didn't previously exist.

        Contrary to SWHListerBase, we don't actually insert the data in
        database. `create_missing_origins_and_tasks` does it once we have the
        origin and task identifiers.
        """
        by_name_version = {}
        temp_packages = []

        area_id = self.area.id

        for model in models_list:
            name = model['name']
            version = model['version']
            temp_packages.append({
                'area_id': area_id,
                'name': name,
                'version': version,
            })
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
        new_packages = self.db_session\
                           .query(TempPackage)\
                           .options(load_only('name', 'version'))\
                           .filter(~exists_tmp_pkg(self.db_session, Package))\
                           .all()

        self.old_area_packages = self.db_session.query(Package).filter(
            exists_tmp_pkg(self.db_session, TempPackage)
        ).all()

        self.db_session.execute(DropTable(TempPackage.__table__))

        added_packages = []
        for package in new_packages:
            model = by_name_version[package.name, package.version]

            added_packages.append(Package(area=self.area,
                                          **model))

        self.db_session.add_all(added_packages)
        return added_packages

    def create_missing_origins_and_tasks(self, models_list, added_packages):
        """We create tasks at the end of the full snapshot processing"""
        return

    def create_tasks_for_snapshot(self, snapshot):
        tasks = [
            snapshot.task_for_package(name, versions)
            for name, versions in snapshot.get_packages().items()
        ]

        return self.scheduler.create_tasks(tasks)

    def run(self, distribution, date=None):
        """Run the lister for a given (distribution, area) tuple.

        Args:
            distribution (str): name of the distribution (e.g. "Debian")
            date (datetime.datetime): date the snapshot is taken (defaults to
                                      now)
        """
        distribution = self.db_session\
                           .query(Distribution)\
                           .options(joinedload(Distribution.areas))\
                           .filter(Distribution.name == distribution)\
                           .one_or_none()

        if not distribution:
            raise ValueError("Distribution %s is not registered" %
                             distribution)

        if not distribution.type == 'deb':
            raise ValueError("Distribution %s is not a Debian derivative" %
                             distribution)

        date = date or datetime.datetime.now(tz=datetime.timezone.utc)

        logging.debug('Creating snapshot for distribution %s on date %s' %
                      (distribution, date))

        snapshot = DistributionSnapshot(date=date, distribution=distribution)

        self.db_session.add(snapshot)

        for area in distribution.areas:
            if not area.active:
                continue

            self.area = area

            logging.debug('Processing area %s' % area)

            _, new_area_packages = self.ingest_data(None)
            area_snapshot = AreaSnapshot(snapshot=snapshot, area=area)
            self.db_session.add(area_snapshot)
            area_snapshot.packages.extend(new_area_packages)
            area_snapshot.packages.extend(self.old_area_packages)

        self.create_tasks_for_snapshot(snapshot)

        self.db_session.commit()

        return True
