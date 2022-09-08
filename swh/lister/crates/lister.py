# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information
from dataclasses import asdict, dataclass
import datetime
import io
import json
import logging
from pathlib import Path
import shutil
from typing import Any, Dict, Iterator, List, Optional
from urllib.parse import urlparse

from dulwich import porcelain
from dulwich.patch import write_tree_diff
from dulwich.repo import Repo

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, Lister

logger = logging.getLogger(__name__)

# Aliasing the page results returned by `get_pages` method from the lister.
CratesListerPage = List[Dict[str, Any]]


@dataclass
class CratesListerState:
    """Store lister state for incremental mode operations.
    'last_commit' represents a git commit hash
    """

    last_commit: str = ""


class CratesLister(Lister[CratesListerState, CratesListerPage]):
    """List origins from the "crates.io" forge.

    It basically fetches https://github.com/rust-lang/crates.io-index.git to a
    temp directory and then walks through each file to get the crate's info on
    the first run.

    In incremental mode, it relies on the same Git repository but instead of reading
    each file of the repo, it get the differences through ``git log last_commit..HEAD``.
    Resulting output string is parsed to build page entries.
    """

    # Part of the lister API, that identifies this lister
    LISTER_NAME = "crates"
    # (Optional) CVS type of the origins listed by this lister, if constant
    VISIT_TYPE = "crates"

    INSTANCE = "crates"
    INDEX_REPOSITORY_URL = "https://github.com/rust-lang/crates.io-index.git"
    DESTINATION_PATH = Path("/tmp/crates.io-index")
    CRATE_FILE_URL_PATTERN = (
        "https://static.crates.io/crates/{crate}/{crate}-{version}.crate"
    )
    CRATE_API_URL_PATTERN = "https://crates.io/api/v1/crates/{crate}"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        credentials: CredentialsType = None,
    ):
        super().__init__(
            scheduler=scheduler,
            credentials=credentials,
            url=self.INDEX_REPOSITORY_URL,
            instance=self.INSTANCE,
        )

    def state_from_dict(self, d: Dict[str, Any]) -> CratesListerState:
        if "last_commit" not in d:
            d["last_commit"] = ""
        return CratesListerState(**d)

    def state_to_dict(self, state: CratesListerState) -> Dict[str, Any]:
        return asdict(state)

    def get_index_repository(self) -> None:
        """Get crates.io-index repository up to date running git command."""
        if self.DESTINATION_PATH.exists():
            porcelain.pull(
                self.DESTINATION_PATH, remote_location=self.INDEX_REPOSITORY_URL
            )
        else:
            porcelain.clone(
                source=self.INDEX_REPOSITORY_URL, target=self.DESTINATION_PATH
            )

    def get_crates_index(self) -> List[Path]:
        """Build a sorted list of file paths excluding dotted directories and
        dotted files.

        Each file path corresponds to a crate that lists all available
        versions.
        """
        crates_index = sorted(
            path
            for path in self.DESTINATION_PATH.rglob("*")
            if not any(part.startswith(".") for part in path.parts)
            and path.is_file()
            and path != self.DESTINATION_PATH / "config.json"
        )

        return crates_index

    def get_last_commit_hash(self, repository_path: Path) -> str:
        """Returns the last commit hash of a git repository"""
        assert repository_path.exists()

        repo = Repo(str(repository_path))
        head = repo.head()
        last_commit = repo[head]

        return last_commit.id.decode()

    def get_last_update_by_file(self, filepath: Path) -> Optional[datetime.datetime]:
        """Given a file path within a Git repository, returns its last commit
        date as iso8601
        """
        repo = Repo(str(self.DESTINATION_PATH))
        # compute relative path otherwise it fails
        relative_path = filepath.relative_to(self.DESTINATION_PATH)
        walker = repo.get_walker(paths=[bytes(relative_path)], max_entries=1)
        try:
            commit = next(iter(walker)).commit
        except StopIteration:
            logger.error(
                "Can not find %s related commits in repository %s", relative_path, repo
            )
            return None
        else:
            last_update = datetime.datetime.fromtimestamp(
                commit.author_time, datetime.timezone.utc
            )
            return last_update

    def page_entry_dict(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Transform package version definition dict to a suitable
        page entry dict
        """
        return dict(
            name=entry["name"],
            version=entry["vers"],
            checksum=entry["cksum"],
            yanked=entry["yanked"],
            crate_file=self.CRATE_FILE_URL_PATTERN.format(
                crate=entry["name"], version=entry["vers"]
            ),
        )

    def get_pages(self) -> Iterator[CratesListerPage]:
        """Yield an iterator sorted by name in ascending order of pages.

        Each page is a list of crate versions with:
            - name: Name of the crate
            - version: Version
            - checksum: Checksum
            - crate_file: Url of the crate file
            - last_update: Date of the last commit of the corresponding index
                file
        """
        # Fetch crates.io index repository
        self.get_index_repository()
        if not self.state.last_commit:
            # First discovery
            # List all crates files from the index repository
            crates_index = self.get_crates_index()
        else:
            # Incremental case
            # Get new package version by parsing a range of commits from index repository
            repo = Repo(str(self.DESTINATION_PATH))
            head = repo[repo.head()]
            last = repo[self.state.last_commit.encode()]

            outstream = io.BytesIO()
            write_tree_diff(outstream, repo.object_store, last.tree, head.tree)
            raw_diff = outstream.getvalue()
            crates_index = []
            for line in raw_diff.splitlines():
                if line.startswith(b"+++ b/"):
                    filepath = line.split(b"+++ b/", 1)[1]
                    crates_index.append(self.DESTINATION_PATH / filepath.decode())
            crates_index = sorted(crates_index)

        logger.debug("Found %s crates in crates_index", len(crates_index))

        # Each line of a crate file is a json entry describing released versions
        # for a package
        for crate in crates_index:
            page = []
            last_update = self.get_last_update_by_file(crate)

            with crate.open("rb") as current_file:
                for line in current_file:
                    data = json.loads(line)
                    entry = self.page_entry_dict(data)
                    entry["last_update"] = last_update
                    page.append(entry)
            yield page

    def get_origins_from_page(self, page: CratesListerPage) -> Iterator[ListedOrigin]:
        """Iterate on all crate pages and yield ListedOrigin instances."""

        assert self.lister_obj.id is not None

        url = self.CRATE_API_URL_PATTERN.format(crate=page[0]["name"])
        last_update = page[0]["last_update"]
        artifacts = []
        crates_metadata = []

        for version in page:
            filename = urlparse(version["crate_file"]).path.split("/")[-1]
            # Build an artifact entry following original-artifacts-json specification
            # https://docs.softwareheritage.org/devel/swh-storage/extrinsic-metadata-specification.html#original-artifacts-json  # noqa: B950
            artifact = {
                "filename": f"{filename}",
                "checksums": {
                    "sha256": f"{version['checksum']}",
                },
                "url": version["crate_file"],
                "version": version["version"],
            }
            artifacts.append(artifact)
            data = {f"{version['version']}": {"yanked": f"{version['yanked']}"}}
            crates_metadata.append(data)

        yield ListedOrigin(
            lister_id=self.lister_obj.id,
            visit_type=self.VISIT_TYPE,
            url=url,
            last_update=last_update,
            extra_loader_arguments={
                "artifacts": artifacts,
                "crates_metadata": crates_metadata,
            },
        )

    def finalize(self) -> None:
        last = self.get_last_commit_hash(repository_path=self.DESTINATION_PATH)
        if self.state.last_commit == last:
            self.updated = False
        else:
            self.state.last_commit = last
            self.updated = True

        logger.debug("Listing crates origin completed with last commit id %s", last)

        # Cleanup by removing the repository directory
        if self.DESTINATION_PATH.exists():
            shutil.rmtree(self.DESTINATION_PATH)
            logger.debug(
                "Successfully removed %s directory", str(self.DESTINATION_PATH)
            )
