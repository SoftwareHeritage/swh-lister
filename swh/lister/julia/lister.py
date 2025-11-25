# Copyright (C) 2023-2025  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from dataclasses import asdict, dataclass
import datetime
import logging
from pathlib import Path
import shutil
import tempfile
from typing import Any, Dict, Iterator, Optional, Tuple

from dulwich import porcelain
from dulwich.objects import Commit
from dulwich.repo import Repo
from dulwich.walk import WalkEntry
import iso8601
import toml

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, Lister

logger = logging.getLogger(__name__)

# Aliasing the page results returned by `get_pages` method from the lister.
JuliaListerPage = Tuple[str, str]


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

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: str = REPO_URL,
        instance: str = INSTANCE,
        credentials: Optional[CredentialsType] = None,
        max_origins_per_page: Optional[int] = None,
        max_pages: Optional[int] = None,
        enable_origins: bool = True,
        # if not provided, a temporary directory is used to clone the
        # git repository of Julia packages
        git_repo_path: Optional[str] = None,
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

        self.remove_git_repo = git_repo_path is None
        if git_repo_path is not None:
            self.repo_path = Path(git_repo_path)
        else:
            self.repo_path = Path(tempfile.mkdtemp(), "General")

    def get_registry_repository(self) -> None:
        """Get Julia General Registry Git repository up to date on disk"""
        try:
            porcelain.clone(
                source=self.url,
                target=self.repo_path,
                errstream=porcelain.NoneStream(),
            )
        except FileExistsError:
            porcelain.pull(
                self.repo_path,
                remote_location=self.url,
                errstream=porcelain.NoneStream(),
            )

    def state_from_dict(self, d: Dict[str, Any]) -> JuliaListerState:
        return JuliaListerState(**d)

    def state_to_dict(self, state: JuliaListerState) -> Dict[str, Any]:
        return asdict(state)

    def get_origin_data(self, entry: WalkEntry) -> Tuple[str, str]:
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
                if change and hasattr(change, "new") and change.new is not None:
                    if change.new.path.endswith(b"/Package.toml"):
                        package_toml = self.repo_path / change.new.path.decode()
                        break
                    elif change.new.path.endswith(b"/Versions.toml"):
                        versions_path = self.repo_path / change.new.path.decode()
                        if versions_path.exists():
                            package_path, _ = change.new.path.decode().split(
                                "Versions.toml"
                            )
                            package_toml = (
                                self.repo_path / package_path / "Package.toml"
                            )
                            break

            if package_toml and package_toml.exists():
                origin = toml.load(package_toml)["repo"]
                last_update = datetime.datetime.fromtimestamp(
                    entry.commit.commit_time,
                    tz=datetime.timezone.utc,
                ).isoformat()
                return (origin, last_update)

        return ("", "")

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
        assert self.repo_path.exists()

        repo = Repo(str(self.repo_path))

        # Detect commits related to new package and new versions since last_seen_commit
        if not self.state.last_seen_commit:
            walker = repo.get_walker()
        else:
            last = repo[self.state.last_seen_commit.encode()]
            assert isinstance(last, Commit)
            walker = repo.get_walker(since=last.commit_time, exclude=[last.id])

        assert walker
        for entry in walker:
            yield self.get_origin_data(entry=entry)

    def get_origins_from_page(self, page: JuliaListerPage) -> Iterator[ListedOrigin]:
        """Iterate on all pages and yield ListedOrigin instances

        Each directory of the Git repository have a ``Package.toml`` file from
        where we get the Git repository url as an origin for each package.
        """
        assert self.lister_obj.id is not None

        origin, last_update = page
        if origin:
            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                visit_type=self.VISIT_TYPE,
                url=origin,
                last_update=iso8601.parse_date(last_update),
            )

    def finalize(self) -> None:
        # Get Git HEAD commit hash
        repo = Repo(str(self.repo_path))
        self.state.last_seen_commit = repo.head().decode("ascii")
        self.updated = True
        # Rm tmp directory repo_path
        if self.repo_path.exists() and self.remove_git_repo:
            shutil.rmtree(self.repo_path)
