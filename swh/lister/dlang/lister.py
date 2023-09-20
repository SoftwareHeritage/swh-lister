# Copyright (C) 2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging
from typing import Any, Dict, Iterator, List, Optional

import iso8601

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, StatelessLister

logger = logging.getLogger(__name__)

# Aliasing the page results returned by `get_pages` method from the lister.
DlangListerPage = List[Dict[str, Any]]


class DlangLister(StatelessLister[DlangListerPage]):
    """List D lang origins."""

    LISTER_NAME = "dlang"
    VISIT_TYPE = "git"  # D lang origins url are Git repositories
    INSTANCE = "dlang"

    BASE_URL = "https://code.dlang.org"
    PACKAGES_DUMP_URL_PATTERN = "{url}/api/packages/dump"
    KINDS = {
        "github": "https://github.com",
        "gitlab": "https://gitlab.com",
        "bitbucket": "https://bitbucket.com",
    }
    KIND_URL_PATTERN = "{url}/{owner}/{project}"

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
            url=self.PACKAGES_DUMP_URL_PATTERN.format(url=url),
            max_origins_per_page=max_origins_per_page,
            max_pages=max_pages,
            enable_origins=enable_origins,
        )
        self.session.headers.update({"Accept": "application/json"})

    def get_pages(self) -> Iterator[DlangListerPage]:
        """Yield an iterator which returns 'page'

        It uses the api endpoint provided by `https://registry.dlang.io/packages`
        to get a list of package names with an origin url that corresponds to Git
        repository.

        There is only one page that list all origins urls.
        """
        response = self.http_request(self.url)
        yield response.json()

    def get_origins_from_page(self, page: DlangListerPage) -> Iterator[ListedOrigin]:
        """Iterate on all pages and yield ListedOrigin instances"""
        assert self.lister_obj.id is not None

        for entry in page:
            repo: Dict[str, Any] = entry["repository"]
            kind: str = repo["kind"]

            if kind not in self.KINDS:
                logging.error("Can not build a repository url with %r" % repo)
                continue

            repo_url = self.KIND_URL_PATTERN.format(
                url=self.KINDS[kind], owner=repo["owner"], project=repo["project"]
            )

            last_update = iso8601.parse_date(entry["stats"]["updatedAt"])

            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                visit_type=self.VISIT_TYPE,
                url=repo_url,
                last_update=last_update,
            )
