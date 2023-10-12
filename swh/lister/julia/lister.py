# Copyright (C) 2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging
from pathlib import Path
import shutil
import tempfile
from typing import Any, Iterator, List, Optional, Tuple

from dulwich import porcelain
import toml

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, StatelessLister

logger = logging.getLogger(__name__)

# Aliasing the page results returned by `get_pages` method from the lister.
JuliaListerPage = List[Tuple[str, Any]]


class JuliaLister(StatelessLister[JuliaListerPage]):
    """List Julia packages origins"""

    LISTER_NAME = "julia"
    VISIT_TYPE = "git"  # Julia origins url are Git repositories
    INSTANCE = "julia"

    REPO_URL = (
        "https://github.com/JuliaRegistries/General.git"  # Julia General Registry
    )
    REPO_PATH = Path(tempfile.mkdtemp(), "General")
    REGISTRY_PATH = REPO_PATH / "Registry.toml"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: str = REPO_URL,
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

    def get_registry_repository(self) -> None:
        """Get Julia General Registry Git repository up to date on disk"""
        try:
            porcelain.clone(source=self.url, target=self.REPO_PATH)
        except FileExistsError:
            porcelain.pull(self.REPO_PATH, remote_location=self.url)

    def get_pages(self) -> Iterator[JuliaListerPage]:
        """Yield an iterator which returns 'page'

        To build a list of origins the `Julia General registry` Git
        repository is cloned to get a `Registry.toml` file, an index file of
        packages directories.

        There is only one page that list all origins urls.
        """
        self.get_registry_repository()
        assert self.REGISTRY_PATH.exists()
        registry = toml.load(self.REGISTRY_PATH)
        yield registry["packages"].items()

    def get_origins_from_page(self, page: JuliaListerPage) -> Iterator[ListedOrigin]:
        """Iterate on all pages and yield ListedOrigin instances

        Each directory of the Git repository have a `Package.toml` file from
        where we get the Git repository url for each package.
        """
        assert self.lister_obj.id is not None
        assert self.REPO_PATH.exists()

        for uuid, info in page:
            package_info_path = self.REPO_PATH / info["path"] / "Package.toml"
            package_info = toml.load(package_info_path)
            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                visit_type=self.VISIT_TYPE,
                url=package_info["repo"],
                last_update=None,
            )

    def finalize(self) -> None:
        # Rm tmp directory REPO_PATH
        if self.REPO_PATH.exists():
            shutil.rmtree(self.REPO_PATH)
        assert not self.REPO_PATH.exists()
