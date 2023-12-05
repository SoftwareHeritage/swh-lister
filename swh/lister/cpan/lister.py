# Copyright (C) 2022-2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from collections import defaultdict
from datetime import datetime
import logging
from typing import Any, Dict, Iterator, List, Optional, Set, Union

import iso8601

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, StatelessLister

logger = logging.getLogger(__name__)

# Aliasing the page results returned by `get_pages` method from the lister.
CpanListerPage = Set[str]


def get_field_value(entry, field_name):
    """
    Splits ``field_name`` on ``.``, and use it as path in the nested ``entry``
    dictionary. If a value does not exist, returns None.

    >>> entry = {"_source": {"foo": 1, "bar": {"baz": 2, "qux": [3]}}}
    >>> get_field_value(entry, "foo")
    1
    >>> get_field_value(entry, "bar")
    {'baz': 2, 'qux': [3]}
    >>> get_field_value(entry, "bar.baz")
    2
    >>> get_field_value(entry, "bar.qux")
    3
    """
    fields = field_name.split(".")
    field_value = entry["_source"]
    for field in fields[:-1]:
        field_value = field_value.get(field, {})
    field_value = field_value.get(fields[-1])
    # scrolled results might have field value in a list
    if isinstance(field_value, list):
        field_value = field_value[0]
    return field_value


def get_module_version(
    module_name: str, module_version: Union[str, float, int], release_name: str
) -> str:
    # some old versions fail to be parsed and cpan api set version to 0
    if module_version == 0:
        prefix = f"{module_name}-"
        if release_name.startswith(prefix):
            # extract version from release name
            module_version = release_name.replace(prefix, "", 1)
    return str(module_version)


class CpanLister(StatelessLister[CpanListerPage]):
    """The Cpan lister list origins from 'Cpan', the Comprehensive Perl Archive
    Network."""

    LISTER_NAME = "cpan"
    VISIT_TYPE = "cpan"
    INSTANCE = "cpan"

    API_BASE_URL = "https://fastapi.metacpan.org/v1"
    REQUIRED_DOC_FIELDS = [
        "download_url",
        "checksum_sha256",
        "distribution",
        "version",
    ]
    OPTIONAL_DOC_FIELDS = ["date", "author", "stat.size", "name", "metadata.author"]
    ORIGIN_URL_PATTERN = "https://metacpan.org/dist/{module_name}"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: str = API_BASE_URL,
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

        self.artifacts: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.module_metadata: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.release_dates: Dict[str, List[datetime]] = defaultdict(list)
        self.module_names: Set[str] = set()

    def process_release_page(self, page: List[Dict[str, Any]]):
        for entry in page:
            if "_source" not in entry or not all(
                k in entry["_source"].keys() for k in self.REQUIRED_DOC_FIELDS
            ):
                logger.warning(
                    "Skipping release entry %s as some required fields are missing",
                    entry.get("_source"),
                )
                continue

            module_name = get_field_value(entry, "distribution")
            module_version = get_field_value(entry, "version")
            module_download_url = get_field_value(entry, "download_url")
            module_sha256_checksum = get_field_value(entry, "checksum_sha256")
            module_date = get_field_value(entry, "date")
            module_size = get_field_value(entry, "stat.size")
            module_author = get_field_value(entry, "author")
            module_author_fullname = get_field_value(entry, "metadata.author")
            release_name = get_field_value(entry, "name")

            module_version = get_module_version(
                module_name, module_version, release_name
            )

            self.artifacts[module_name].append(
                {
                    "url": module_download_url,
                    "filename": module_download_url.split("/")[-1],
                    "checksums": {"sha256": module_sha256_checksum},
                    "version": module_version,
                    "length": module_size,
                }
            )

            self.module_metadata[module_name].append(
                {
                    "name": module_name,
                    "version": module_version,
                    "cpan_author": module_author,
                    "author": (
                        module_author_fullname
                        if module_author_fullname not in (None, "", "unknown")
                        else module_author
                    ),
                    "date": module_date,
                    "release_name": release_name,
                }
            )

            self.release_dates[module_name].append(iso8601.parse_date(module_date))

            self.module_names.add(module_name)

    def get_pages(self) -> Iterator[CpanListerPage]:
        """Yield an iterator which returns 'page'"""

        endpoint = f"{self.API_BASE_URL}/release/_search"
        scrollendpoint = f"{self.API_BASE_URL}/_search/scroll"
        size = 1000

        res = self.http_request(
            endpoint,
            params={
                "_source": self.REQUIRED_DOC_FIELDS + self.OPTIONAL_DOC_FIELDS,
                "size": size,
                "scroll": "1m",
            },
        )
        data = res.json()["hits"]["hits"]
        self.process_release_page(data)

        _scroll_id = res.json()["_scroll_id"]

        while data:
            scroll_res = self.http_request(
                scrollendpoint, params={"scroll": "1m", "scroll_id": _scroll_id}
            )
            data = scroll_res.json()["hits"]["hits"]
            _scroll_id = scroll_res.json()["_scroll_id"]
            self.process_release_page(data)

        yield self.module_names

    def get_origins_from_page(
        self, module_names: CpanListerPage
    ) -> Iterator[ListedOrigin]:
        """Iterate on all pages and yield ListedOrigin instances."""
        assert self.lister_obj.id is not None

        for module_name in module_names:
            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                visit_type=self.VISIT_TYPE,
                url=self.ORIGIN_URL_PATTERN.format(module_name=module_name),
                last_update=max(self.release_dates[module_name]),
                extra_loader_arguments={
                    "api_base_url": self.API_BASE_URL,
                    "artifacts": self.artifacts[module_name],
                    "module_metadata": self.module_metadata[module_name],
                },
            )
