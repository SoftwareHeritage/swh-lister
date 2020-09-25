# Copyright (C) 2017-2019 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import binascii
from collections import defaultdict
import datetime
from typing import Any, Mapping

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Table,
    UniqueConstraint,
)

try:
    from sqlalchemy import JSON
except ImportError:
    # SQLAlchemy < 1.1
    from sqlalchemy.dialects.postgresql import JSONB as JSON

from sqlalchemy.orm import relationship

from swh.lister.core.models import SQLBase


class Distribution(SQLBase):
    """A distribution (e.g. Debian, Ubuntu, Fedora, ...)"""

    __tablename__ = "distribution"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    type = Column(Enum("deb", "rpm", name="distribution_types"), nullable=False)
    mirror_uri = Column(String, nullable=False)

    areas = relationship("Area", back_populates="distribution")

    def origin_for_package(self, package_name: str) -> str:
        """Return the origin url for the given package

        """
        return "%s://%s/packages/%s" % (self.type, self.name, package_name)

    def __repr__(self):
        return "Distribution(%s (%s) on %s)" % (self.name, self.type, self.mirror_uri,)


class Area(SQLBase):
    __tablename__ = "area"
    __table_args__ = (UniqueConstraint("distribution_id", "name"),)

    id = Column(Integer, primary_key=True)
    distribution_id = Column(Integer, ForeignKey("distribution.id"), nullable=False)
    name = Column(String, nullable=False)
    active = Column(Boolean, nullable=False, default=True)

    distribution = relationship("Distribution", back_populates="areas")

    def index_uris(self):
        """Get possible URIs for this component's package index"""
        if self.distribution.type == "deb":
            compression_exts = ("xz", "bz2", "gz", None)
            base_uri = "%s/dists/%s/source/Sources" % (
                self.distribution.mirror_uri,
                self.name,
            )
            for ext in compression_exts:
                if ext:
                    yield (base_uri + "." + ext, ext)
                else:
                    yield (base_uri, None)
        else:
            raise NotImplementedError(
                "Do not know how to build index URI for Distribution type %s"
                % self.distribution.type
            )

    def __repr__(self):
        return "Area(%s of %s)" % (self.name, self.distribution.name,)


class Package(SQLBase):
    __tablename__ = "package"
    __table_args__ = (UniqueConstraint("area_id", "name", "version"),)

    id = Column(Integer, primary_key=True)
    area_id = Column(Integer, ForeignKey("area.id"), nullable=False)
    name = Column(String, nullable=False)
    version = Column(String, nullable=False)
    directory = Column(String, nullable=False)
    files = Column(JSON, nullable=False)

    origin_id = Column(Integer)
    task_id = Column(Integer)

    revision_id = Column(LargeBinary(20))

    area = relationship("Area")

    @property
    def distribution(self):
        return self.area.distribution

    def fetch_uri(self, filename):
        """Get the URI to fetch the `filename` file associated with the
        package"""
        if self.distribution.type == "deb":
            return "%s/%s/%s" % (
                self.distribution.mirror_uri,
                self.directory,
                filename,
            )
        else:
            raise NotImplementedError(
                "Do not know how to build fetch URI for Distribution type %s"
                % self.distribution.type
            )

    def loader_dict(self):
        ret = {
            "id": self.id,
            "name": self.name,
            "version": self.version,
        }
        if self.revision_id:
            ret["revision_id"] = binascii.hexlify(self.revision_id).decode()
        else:
            files = {name: checksums.copy() for name, checksums in self.files.items()}
            for name in files:
                files[name]["uri"] = self.fetch_uri(name)

            ret.update(
                {"revision_id": None, "files": files,}
            )
        return ret

    def __repr__(self):
        return "Package(%s_%s of %s %s)" % (
            self.name,
            self.version,
            self.distribution.name,
            self.area.name,
        )


class DistributionSnapshot(SQLBase):
    __tablename__ = "distribution_snapshot"

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False, index=True)
    distribution_id = Column(Integer, ForeignKey("distribution.id"), nullable=False)

    distribution = relationship("Distribution")
    areas = relationship("AreaSnapshot", back_populates="snapshot")

    def task_for_package(
        self, package_name: str, package_versions: Mapping
    ) -> Mapping[str, Any]:
        """Return the task dictionary for the given list of package versions

        """
        origin_url = self.distribution.origin_for_package(package_name)

        return {
            "policy": "oneshot",
            "type": "load-%s-package" % self.distribution.type,
            "next_run": datetime.datetime.now(tz=datetime.timezone.utc),
            "arguments": {
                "args": [],
                "kwargs": {
                    "url": origin_url,
                    "date": self.date.isoformat(),
                    "packages": package_versions,
                },
            },
            "retries_left": 3,
        }

    def get_packages(self):
        packages = defaultdict(dict)
        for area_snapshot in self.areas:
            area_name = area_snapshot.area.name
            for package in area_snapshot.packages:
                ref_name = "%s/%s" % (area_name, package.version)
                packages[package.name][ref_name] = package.loader_dict()

        return packages


area_snapshot_package_assoc = Table(
    "area_snapshot_package",
    SQLBase.metadata,
    Column("area_snapshot_id", Integer, ForeignKey("area_snapshot.id"), nullable=False),
    Column("package_id", Integer, ForeignKey("package.id"), nullable=False),
)


class AreaSnapshot(SQLBase):
    __tablename__ = "area_snapshot"

    id = Column(Integer, primary_key=True)
    snapshot_id = Column(
        Integer, ForeignKey("distribution_snapshot.id"), nullable=False
    )
    area_id = Column(Integer, ForeignKey("area.id"), nullable=False)

    snapshot = relationship("DistributionSnapshot", back_populates="areas")
    area = relationship("Area")
    packages = relationship("Package", secondary=area_snapshot_package_assoc)


class TempPackage(SQLBase):
    __tablename__ = "temp_package"
    __table_args__ = {
        "prefixes": ["TEMPORARY"],
    }

    id = Column(Integer, primary_key=True)
    area_id = Column(Integer)
    name = Column(String)
    version = Column(String)
