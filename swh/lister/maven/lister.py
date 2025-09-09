# Copyright (C) 2021-2025 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import gzip
import logging
import os
import re
import shutil
import subprocess
import tempfile
from typing import Any, Dict, Iterator, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from lxml import etree
import ndjson
import requests

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, Lister

logger = logging.getLogger(__name__)

RepoPage = Optional[Dict[str, Any]]

SUPPORTED_SCM_TYPES = ("git", "svn", "hg", "cvs", "bzr")


@dataclass
class MavenListerState:
    """State of the MavenLister"""

    last_seen_doc: int = -1
    """Last doc ID ingested during an incremental pass

    """

    last_seen_pom: int = -1
    """Last doc ID related to a pom and ingested during
       an incremental pass

    """


class MavenLister(Lister[MavenListerState, RepoPage]):
    """List origins from a Maven repository.

    Maven Central provides artifacts for Java builds.
    It includes POM files and source archives, which we download to get
    the source code of artifacts and links to their scm repository.

    This lister yields origins of types: git/svn/hg or whatever the Artifacts
    use as repository type, plus maven types for the maven loader (tarball, source jar).

    The lister relies on the use of the maven index exporter tool allowing to
    convert the binary content of a maven repository index to NDJSON format
    (https://gitlab.softwareheritage.org/swh/devel/fixtures/maven-index-exporter).
    To be able to execute the tool, Java runtime environment >= 17 must be available
    in the lister execution environment.
    """

    LISTER_NAME = "maven"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: str,
        # keep no longer used parameter for backward compatibility of
        # existing lister tasks in scheduler database
        index_url: Optional[str] = None,
        instance: Optional[str] = None,
        credentials: CredentialsType = None,
        max_origins_per_page: Optional[int] = None,
        max_pages: Optional[int] = None,
        enable_origins: bool = True,
        incremental: bool = True,
        with_github_session=True,
        process_pom_files: bool = True,
    ):
        """Lister class for Maven repositories.

        Args:
            url: main URL of the Maven repository, i.e. url of the base index
                used to fetch maven artifacts. For Maven central use
                https://repo1.maven.org/maven2/
            instance: Name of maven instance. Defaults to url's network location
                if unset.
            incremental: defaults to :const:`True`. Defines if incremental listing
                is activated or not.
            with_github_session: defaults to :const:`True`. Defines if canonical
                URL for extracted github repository should be retrieved with the
                GitHub REST API.
        """
        self.BASE_URL = url.rstrip("/") + "/"
        self.incremental = incremental

        super().__init__(
            scheduler=scheduler,
            credentials=credentials,
            url=self.BASE_URL,
            instance=instance,
            with_github_session=with_github_session,
            max_origins_per_page=max_origins_per_page,
            max_pages=max_pages,
            enable_origins=enable_origins,
        )

        self.session.headers.update({"Accept": "application/json"})

        self.jar_origin: Optional[ListedOrigin] = None
        self.jar_origin_docs: List[int] = []
        self.last_origin_url: Optional[str] = None
        self.last_seen_doc = self.state.last_seen_doc
        self.last_seen_pom = self.state.last_seen_pom
        self.process_pom_files = process_pom_files

    def state_from_dict(self, d: Dict[str, Any]) -> MavenListerState:
        return MavenListerState(**d)

    def state_to_dict(self, state: MavenListerState) -> Dict[str, Any]:
        return asdict(state)

    def get_pages(self) -> Iterator[RepoPage]:
        """Retrieve and parse exported maven indexes to
        identify all pom files and src archives.
        """

        # Example of returned RepoPage's:
        # [
        #   {
        #     "type": "maven",
        #     "url": "https://maven.xwiki.org/..-5.4.2-sources.jar",
        #     "time": 1626109619335,
        #     "gid": "org.xwiki.platform",
        #     "aid": "xwiki-platform-wikistream-events-xwiki",
        #     "version": "5.4.2"
        #   },
        #   {
        #     "type": "scm",
        #     "url": "scm:git:git://github.com/openengsb/openengsb-framework.git",
        #     "project": "openengsb-framework",
        #   },
        #   ...
        # ]

        out_pom: Dict = {}

        with tempfile.TemporaryDirectory() as tmpdir:

            work_dir = os.path.join(tmpdir, "work")
            publish_dir = os.path.join(tmpdir, "publish")
            os.makedirs(work_dir, exist_ok=True)
            os.makedirs(publish_dir, exist_ok=True)

            # Execute maven index exporter tool to dump maven repository
            # index to NDJSON format
            subprocess.check_call(
                [
                    "python3",
                    "/opt/maven-index-exporter/run_full_export.py",
                    "--base-url",
                    self.BASE_URL,
                    "--work-dir",
                    work_dir,
                    "--publish-dir",
                    publish_dir,
                ],
            )

            # Remove no longer needed files to save some disk space
            shutil.rmtree(work_dir)

            # Read NDJSON file line by line and process it, documents are sorted
            # by groupId and artifactId so every versions of a given maven package
            # are processed sequentially.
            with gzip.open(
                os.path.join(publish_dir, "maven-index-export.ndjson.gz"),
                mode="rt",
                encoding="utf-8",
                errors="ignore",
            ) as f:
                reader = ndjson.reader(f)
                for entry in reader:
                    doc_id = entry["doc"]
                    gid, aid, version, classifier, ext = entry["u"].split("|")
                    ext = ext.strip()
                    path = "/".join(gid.split("."))
                    if (
                        self.process_pom_files
                        and classifier == "NA"
                        and ext.lower() == "pom"
                    ):
                        # Store pom file URL to extract SCM URLs at end of listing
                        # process.If incremental mode, we don't record any pom file
                        # that is before our last recorded doc id.
                        if self.incremental and self.last_seen_pom >= doc_id:
                            continue
                        url_path = f"{path}/{aid}/{version}/{aid}-{version}.{ext}"
                        url_pom = urljoin(
                            self.BASE_URL,
                            url_path,
                        )
                        out_pom[url_pom] = doc_id
                    elif (
                        classifier.lower() == "sources" or ("src" in classifier)
                    ) and ext.lower() in ("zip", "jar"):
                        # Yield maven source package info
                        url_path = (
                            f"{path}/{aid}/{version}/{aid}-{version}-{classifier}.{ext}"
                        )
                        url_src = urljoin(self.BASE_URL, url_path)
                        m_time = entry["i"].split("|")[1]
                        artifact_metadata_d = {
                            "type": "maven",
                            "url": url_src,
                            "doc": doc_id,
                            "gid": gid,
                            "aid": aid,
                            "version": version,
                            "time": int(m_time),
                        }
                        logger.debug(
                            "* Yielding jar %s: %s", url_src, artifact_metadata_d
                        )
                        yield artifact_metadata_d

        # Notify that maven index listing has finished
        yield None

        if self.process_pom_files:
            # Now fetch pom files and scan them for scm info.
            logger.info("Found %s poms.", len(out_pom))
            logger.info("Fetching poms ...")
            for pom_url in out_pom:
                try:
                    response = self.http_request(pom_url)
                    parsed_pom = BeautifulSoup(response.content, "xml")
                    connection = parsed_pom.select_one("project scm connection")
                    if connection is not None:
                        artifact_metadata_d = {
                            "type": "scm",
                            "doc": out_pom[pom_url],
                            "url": connection.text,
                        }
                        logger.debug(
                            "* Yielding pom %s: %s", pom_url, artifact_metadata_d
                        )
                        yield artifact_metadata_d
                    else:
                        logger.debug("No project.scm.connection in pom %s", pom_url)
                except requests.HTTPError:
                    logger.warning(
                        "POM info page could not be fetched, skipping project '%s'",
                        pom_url,
                    )
                except etree.Error as error:
                    logger.info("Could not parse POM %s XML: %s.", pom_url, error)

    def get_scm(self, page: RepoPage) -> Optional[ListedOrigin]:
        """Retrieve scm origin out of the page information. Only called when type of the
        page is scm.

        Try and detect an scm/vcs repository. Note that official format is in the form:
        scm:{type}:git://example.org/{user}/{repo}.git but some projects directly put
        the repo url (without the "scm:type"), so we have to check against the content
        to extract the type and url properly.

        Raises
            AssertionError when the type of the page is not 'scm'

        Returns
            ListedOrigin with proper canonical scm url (for github) if any is found,
            None otherwise.

        """

        assert page and page["type"] == "scm"
        visit_type: Optional[str] = None
        url: Optional[str] = None
        m_scm = re.match(r"^scm:(?P<type>[^:]+):(?P<url>.*)$", page["url"])
        if m_scm is None:
            return None

        scm_type = m_scm.group("type")
        if scm_type and scm_type in SUPPORTED_SCM_TYPES:
            url = m_scm.group("url")
            visit_type = scm_type
        elif page["url"].endswith(".git"):
            url = page["url"].lstrip("scm:")
            visit_type = "git"
        else:
            return None

        if self.github_session and url and visit_type == "git":
            # Non-github urls will be returned as is, github ones will be canonical ones
            url = self.github_session.get_canonical_url(url)

        if not url:
            return None

        if "${" in url:
            # A handful of URLs contain templated strings (21, as of 2023-01-30)
            # We could implement support for
            # https://maven.apache.org/guides/introduction/introduction-to-the-pom.html#Project_Interpolation_and_Variables
            # but most of them seem to use variables not defined in this spec.
            return None

        assert visit_type is not None
        assert self.lister_obj.id is not None
        return ListedOrigin(
            lister_id=self.lister_obj.id,
            url=url,
            visit_type=visit_type,
        )

    def get_origins_from_page(self, page: RepoPage) -> Iterator[ListedOrigin]:
        """Convert a page of Maven repositories into a list of ListedOrigins."""
        if page is None:
            # maven index listing has finished, yield last ListedOrigin if any
            if self.jar_origin and (
                not self.incremental
                or (any(doc > self.last_seen_doc for doc in self.jar_origin_docs))
            ):
                yield self.jar_origin
        elif page["type"] == "scm":
            listed_origin = self.get_scm(page)
            if listed_origin:
                yield listed_origin
        elif page["type"] == "maven":
            # Origin is gathering source archives:
            last_update_dt = None
            last_update_iso = ""
            try:
                last_update_seconds = str(page["time"])[:-3]
                last_update_dt = datetime.fromtimestamp(int(last_update_seconds))
                last_update_dt = last_update_dt.astimezone(timezone.utc)
            except (OverflowError, ValueError):
                logger.warning("- Failed to convert datetime %s.", last_update_seconds)
            if last_update_dt:
                last_update_iso = last_update_dt.isoformat()

            # Origin URL will target page holding sources for all versions of
            # an artifactId (package name) inside a groupId (namespace)
            path = "/".join(page["gid"].split("."))
            origin_url = urljoin(self.BASE_URL, f"{path}/{page['aid']}")

            artifact = {
                **{k: v for k, v in page.items() if k != "doc"},
                "time": last_update_iso,
                "base_url": self.BASE_URL,
            }

            if origin_url != self.last_origin_url:
                # All versions of a given maven package have been processed,
                # current ListedOrigin can be yielded
                if self.jar_origin and (
                    not self.incremental
                    # In incremental mode, yield maven origin only if it has new
                    # versions since last listing
                    or (any(doc > self.last_seen_doc for doc in self.jar_origin_docs))
                ):
                    yield self.jar_origin

                # Keep track of maven index documents ids for package versions
                self.jar_origin_docs = [page["doc"]]

                # Create ListedOrigin instance for newly seen maven package
                assert self.lister_obj.id is not None
                self.jar_origin = ListedOrigin(
                    lister_id=self.lister_obj.id,
                    url=origin_url,
                    visit_type=page["type"],
                    last_update=last_update_dt,
                    extra_loader_arguments={"artifacts": [artifact]},
                )
            elif self.jar_origin:
                # Update list of source artifacts for the current ListedOrigin
                artifacts = self.jar_origin.extra_loader_arguments["artifacts"]
                if artifact not in artifacts:
                    artifacts.append(artifact)
                    self.jar_origin_docs.append(page["doc"])
                if (
                    self.jar_origin.last_update
                    and last_update_dt
                    and last_update_dt > self.jar_origin.last_update
                ):
                    self.jar_origin.last_update = last_update_dt

            self.last_origin_url = origin_url

    def commit_page(self, page: RepoPage) -> None:
        """Update currently stored state using the latest listed doc.

        Note: this is a noop for full listing mode

        """
        if self.incremental and self.state:
            # We need to differentiate the two state counters according
            # to the type of origin.
            if (
                page
                and page["type"] == "maven"
                and page["doc"] > self.state.last_seen_doc
            ):
                self.state.last_seen_doc = page["doc"]
            elif (
                page
                and page["type"] == "scm"
                and page["doc"] > self.state.last_seen_pom
            ):
                self.state.last_seen_doc = page["doc"]
                self.state.last_seen_pom = page["doc"]

    def finalize(self) -> None:
        """Finalize the lister state, set update if any progress has been made.

        Note: this is a noop for full listing mode

        """
        if self.incremental and self.state:
            last_seen_doc = self.state.last_seen_doc
            last_seen_pom = self.state.last_seen_pom

            if last_seen_doc and last_seen_pom:
                if (self.last_seen_doc < last_seen_doc) or (
                    self.last_seen_pom < last_seen_pom
                ):
                    self.updated = True
