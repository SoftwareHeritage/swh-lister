# Copyright (C) 2022-2024  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import base64
from datetime import timezone
import gzip
import logging
import os
import shutil
import subprocess
import tarfile
import tempfile
from typing import Any, Dict, Iterator, Optional, Tuple

from bs4 import BeautifulSoup
import psycopg2
from testing.postgresql import Postgresql

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, StatelessLister

logger = logging.getLogger(__name__)

RubyGemsListerPage = Dict[str, Any]


class RubyGemsLister(StatelessLister[RubyGemsListerPage]):
    """Lister for RubyGems.org, the Ruby community's gem hosting service.

    Instead of querying rubygems.org Web API, it uses gems data from the
    daily PostreSQL database dump of rubygems. It enables to gather all
    interesting info about a gem and its release artifacts (version number,
    download URL, checksums, release date) in an efficient way and without
    flooding rubygems Web API with numerous HTTP requests (as there is more
    than 187000 gems available on 07/10/2022).
    """

    LISTER_NAME = "rubygems"
    VISIT_TYPE = "rubygems"
    INSTANCE = "rubygems"

    RUBY_GEMS_POSTGRES_DUMP_BASE_URL = (
        "https://s3-us-west-2.amazonaws.com/rubygems-dumps"
    )
    RUBY_GEMS_POSTGRES_DUMP_LIST_URL = (
        f"{RUBY_GEMS_POSTGRES_DUMP_BASE_URL}?prefix=production/public_postgresql"
    )

    RUBY_GEM_DOWNLOAD_URL_PATTERN = "https://rubygems.org/downloads/{gem}-{version}.gem"
    RUBY_GEM_ORIGIN_URL_PATTERN = "https://rubygems.org/gems/{gem}"
    RUBY_GEM_EXTRINSIC_METADATA_URL_PATTERN = (
        "https://rubygems.org/api/v2/rubygems/{gem}/versions/{version}.json"
    )

    DB_NAME = "rubygems"
    DUMP_SQL_PATH = "public_postgresql/databases/PostgreSQL.sql.gz"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: str = RUBY_GEMS_POSTGRES_DUMP_BASE_URL,
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

    def get_latest_dump_file(self) -> str:
        response = self.http_request(self.RUBY_GEMS_POSTGRES_DUMP_LIST_URL)
        xml = BeautifulSoup(response.content, "xml")
        contents = xml.select("Contents")
        return contents[-1].select("Key")[0].text

    def create_rubygems_db(
        self, postgresql: Postgresql
    ) -> Tuple[str, psycopg2._psycopg.connection]:
        logger.debug("Creating rubygems database")

        db_dsn = postgresql.dsn()
        db_url = postgresql.url().replace(db_dsn["database"], self.DB_NAME)
        db = psycopg2.connect(**db_dsn)
        db.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        with db.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE {self.DB_NAME}")

        db_dsn["database"] = self.DB_NAME

        db = psycopg2.connect(**db_dsn)
        db.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        with db.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS hstore")

        return db_url, db

    def populate_rubygems_db(self, db_url: str):
        dump_file = self.get_latest_dump_file()
        dump_id = dump_file.split("/")[2]

        response = self.http_request(f"{self.url}/{dump_file}", stream=True)

        with tempfile.TemporaryDirectory() as temp_dir:
            logger.debug(
                "Downloading latest rubygems database dump: %s (%s bytes)",
                dump_id,
                response.headers["content-length"],
            )
            dump_file = os.path.join(temp_dir, "rubygems_dump.tar")
            with open(dump_file, "wb") as dump:
                for chunk in response.iter_content(chunk_size=1024):
                    dump.write(chunk)

            with tarfile.open(dump_file) as dump_tar:
                dump_tar.extractall(temp_dir)

                logger.debug("Populating rubygems database with dump %s", dump_id)

                # FIXME: make this work with -v ON_ERROR_STOP=1
                psql = subprocess.Popen(
                    ["psql", "--no-psqlrc", "-q", db_url],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

                # passing value of gzip.open as stdin of subprocess.run makes the process
                # read raw data instead of decompressed data so we have to use a pipe
                with gzip.open(os.path.join(temp_dir, self.DUMP_SQL_PATH), "rb") as sql:
                    shutil.copyfileobj(sql, psql.stdin)  # type: ignore

                # denote end of read file
                psql.stdin.close()  # type: ignore
                psql.wait()

                if psql.returncode != 0:
                    assert psql.stdout
                    for line in psql.stdout.readlines():
                        logger.warning("psql out: %s", line.decode().strip())
                    assert psql.stderr
                    for line in psql.stderr.readlines():
                        logger.warning("psql err: %s", line.decode().strip())
                    raise ValueError(
                        "Loading rubygems dump failed with exit code %s.",
                        psql.returncode,
                    )

    def get_pages(self) -> Iterator[RubyGemsListerPage]:
        # spawn a temporary postgres instance (require initdb executable in environment)
        with Postgresql() as postgresql:
            db_url, db = self.create_rubygems_db(postgresql)
            self.populate_rubygems_db(db_url)

            with db.cursor() as cursor:
                cursor.execute("SELECT id, name from rubygems")
                for gem_id, gem_name in cursor.fetchall():
                    logger.debug("Processing gem named %s", gem_name)
                    with db.cursor() as cursor_v:
                        cursor_v.execute(
                            "SELECT authors, built_at, number, sha256, size from versions "
                            "where rubygem_id = %s",
                            (gem_id,),
                        )
                        versions = [
                            {
                                "number": number,
                                "url": self.RUBY_GEM_DOWNLOAD_URL_PATTERN.format(
                                    gem=gem_name, version=number
                                ),
                                "date": built_at.replace(tzinfo=timezone.utc),
                                "authors": authors,
                                "sha256": (
                                    base64.decodebytes(sha256.encode()).hex()
                                    if sha256
                                    else None
                                ),
                                "size": size,
                            }
                            for authors, built_at, number, sha256, size in cursor_v.fetchall()
                        ]
                        if versions:
                            yield {
                                "name": gem_name,
                                "versions": versions,
                            }

    def get_origins_from_page(self, page: RubyGemsListerPage) -> Iterator[ListedOrigin]:
        assert self.lister_obj.id is not None

        artifacts = []
        rubygem_metadata = []
        for version in page["versions"]:
            artifacts.append(
                {
                    "version": version["number"],
                    "filename": version["url"].split("/")[-1],
                    "url": version["url"],
                    "checksums": (
                        {"sha256": version["sha256"]} if version["sha256"] else {}
                    ),
                    "length": version["size"],
                }
            )
            rubygem_metadata.append(
                {
                    "version": version["number"],
                    "date": version["date"].isoformat(),
                    "authors": version["authors"],
                    "extrinsic_metadata_url": (
                        self.RUBY_GEM_EXTRINSIC_METADATA_URL_PATTERN.format(
                            gem=page["name"], version=version["number"]
                        )
                    ),
                }
            )

        yield ListedOrigin(
            lister_id=self.lister_obj.id,
            visit_type=self.VISIT_TYPE,
            url=self.RUBY_GEM_ORIGIN_URL_PATTERN.format(gem=page["name"]),
            last_update=max(version["date"] for version in page["versions"]),
            extra_loader_arguments={
                "artifacts": artifacts,
                "rubygem_metadata": rubygem_metadata,
            },
        )
