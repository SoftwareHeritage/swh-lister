# Copyright (C) 2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from dataclasses import asdict, dataclass
import datetime
import logging
from pathlib import Path
import shutil
import tempfile
from typing import Any, Dict, Iterator, Optional

from dulwich import porcelain
from dulwich.repo import Repo
from dulwich.walk import WalkEntry
import iso8601
import toml

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, Lister

logger = logging.getLogger(__name__)

# Aliasing the page results returned by `get_pages` method from the lister.
JuliaListerPage = Dict[str, Any]


@dataclass
class JuliaListerState:
    """Store lister state for incremental mode operations"""

    last_seen_commit: Optional[str] = None
    """Hash of the latest Git commit when lister was executed"""


class JuliaLister(Lister[JuliaListerState, JuliaListerPage]):
    """List Julia packages origins"""

    LISTER_NAME = "julia"
    VISIT_TYPE = "git"  # Julia origins url are Git repositories
    INSTANCE = "julia"

    REPO_URL = (
        "https://github.com/JuliaRegistries/General.git"  # Julia General Registry
    )
    REPO_PATH = Path(tempfile.mkdtemp(), "General")

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

    def state_from_dict(self, d: Dict[str, Any]) -> JuliaListerState:
        return JuliaListerState(**d)

    def state_to_dict(self, state: JuliaListerState) -> Dict[str, Any]:
        return asdict(state)

    def get_origin_data(self, entry: WalkEntry) -> Dict[str, Any]:
        """
        Given an entry object parse its commit message and other attributes
        to detect if the commit is valid to describe a new package or
        a new package version.

        Returns a dict with origin url as key and iso8601 commit date as value
        """
        assert entry

        if (
            entry.commit
            and entry.changes()
            and (
                entry.commit.message.startswith(b"New package: ")
                or entry.commit.message.startswith(b"New version: ")
            )
        ):
            package_toml = None
            for change in entry.changes():
                if change and hasattr(change, "new"):
                    if change.new.path.endswith(b"/Package.toml"):
                        package_toml = self.REPO_PATH / change.new.path.decode()
                        break
                    elif change.new.path.endswith(b"/Versions.toml"):
                        versions_path = self.REPO_PATH / change.new.path.decode()
                        if versions_path.exists():
                            package_path, _ = change.new.path.decode().split(
                                "Versions.toml"
                            )
                            package_toml = (
                                self.REPO_PATH / package_path / "Package.toml"
                            )
                            break

            if package_toml and package_toml.exists():
                origin = toml.load(package_toml)["repo"]
                last_update = datetime.datetime.fromtimestamp(
                    entry.commit.commit_time,
                    tz=datetime.timezone.utc,
                ).isoformat()
                return {f"{origin}": last_update}

        return {}

    def get_pages(self) -> Iterator[JuliaListerPage]:
        """Yield an iterator which returns 'page'

        To build a list of origins the ``Julia General registry`` Git
        repository is cloned to look at commits history to discover new
        package and new package versions.

        Depending on ``last_seen_commit`` state it initiate a commit walker
        since the last time the lister has been executed.

        There is only one page that list all origins urls.
        """
        # Clone the repository
        self.get_registry_repository()
        assert self.REPO_PATH.exists()

        repo = Repo(str(self.REPO_PATH))

        # Detect commits related to new package and new versions since last_seen_commit
        if not self.state.last_seen_commit:
            walker = repo.get_walker()
        else:
            last = repo[self.state.last_seen_commit.encode()]
            walker = repo.get_walker(since=last.commit_time, exclude=[last.id])

        assert walker
        packages = {}
        for entry in walker:
            packages.update(self.get_origin_data(entry=entry))

        yield packages

    def get_origins_from_page(self, page: JuliaListerPage) -> Iterator[ListedOrigin]:
        """Iterate on all pages and yield ListedOrigin instances

        Each directory of the Git repository have a ``Package.toml`` file from
        where we get the Git repository url as an origin for each package.
        """
        assert self.lister_obj.id is not None

        for origin, last_update in page.items():
            last_update = iso8601.parse_date(last_update)
            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                visit_type=self.VISIT_TYPE,
                url=origin,
                last_update=last_update,
            )

    def finalize(self) -> None:
        # Get Git HEAD commit hash
        repo = Repo(str(self.REPO_PATH))
        self.state.last_seen_commit = repo.head().decode("ascii")
        self.updated = True
        # Rm tmp directory REPO_PATH
        if self.REPO_PATH.exists():
            shutil.rmtree(self.REPO_PATH)
        assert not self.REPO_PATH.exists()
