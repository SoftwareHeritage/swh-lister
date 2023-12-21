# Copyright (C) 2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from dataclasses import asdict, dataclass
import logging
from typing import Any, Dict, Iterator, Optional, Set

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, Lister

logger = logging.getLogger(__name__)

# Aliasing the page results returned by `get_pages` method from the lister.
ElmListerPage = Set[str]


@dataclass
class ElmListerState:
    """Store lister state for incremental mode operations"""

    all_packages_count: Optional[int] = None
    """Store the count of all existing packages, used as ``since`` argument of
    API endpoint url.
    """


class ElmLister(Lister[ElmListerState, ElmListerPage]):
    """List Elm packages origins"""

    LISTER_NAME = "elm"
    VISIT_TYPE = "git"  # Elm origins url are Git repositories
    INSTANCE = "elm"

    BASE_URL = "https://package.elm-lang.org"
    ALL_PACKAGES_URL_PATTERN = "{base_url}/all-packages/since/{since}"
    REPO_URL_PATTERN = "https://github.com/{name}"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        credentials: Optional[CredentialsType] = None,
        url: str = BASE_URL,
        instance: str = INSTANCE,
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
        self.all_packages_count: int = 0
        self.session.headers.update({"Accept": "application/json"})

    def state_from_dict(self, d: Dict[str, Any]) -> ElmListerState:
        return ElmListerState(**d)

    def state_to_dict(self, state: ElmListerState) -> Dict[str, Any]:
        return asdict(state)

    def get_pages(self) -> Iterator[ElmListerPage]:
        """Yield an iterator which returns 'page'

        It uses the Http api endpoint ``https://package.elm-lang.org/all-packages/since/:since``
        to get a list of packages versions from where we get names corresponding to GitHub
        repository url suffixes.

        There is only one page that list all origins urls.
        """

        if not self.state.all_packages_count:
            since = 0
        else:
            since = self.state.all_packages_count

        response = self.http_request(
            self.ALL_PACKAGES_URL_PATTERN.format(base_url=self.url, since=since)
        )
        # We’ll save this to the state in finalize()
        self.all_packages_count = len(response.json()) + since

        res = set()
        for entry in response.json():
            res.add(entry.split("@")[0])

        yield res

    def get_origins_from_page(self, page: ElmListerPage) -> Iterator[ListedOrigin]:
        """Iterate on all pages and yield ListedOrigin instances"""
        assert self.lister_obj.id is not None

        for name in page:
            repo_url: str = self.REPO_URL_PATTERN.format(name=name)

            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                visit_type=self.VISIT_TYPE,
                url=repo_url,
                last_update=None,
            )

    def finalize(self) -> None:
        if (
            self.state.all_packages_count is None
            or self.all_packages_count > self.state.all_packages_count
        ):
            self.state.all_packages_count = self.all_packages_count
            self.updated = True
