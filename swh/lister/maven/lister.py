# Copyright (C) 2021-2024 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import logging
import re
from typing import Any, Dict, Iterator, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import lxml
import requests

from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, Lister

logger = logging.getLogger(__name__)

RepoPage = Dict[str, Any]

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
    use as repository type, plus maven types for the maven loader (tgz, jar)."""

    LISTER_NAME = "maven"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: str,
        index_url: str,
        instance: Optional[str] = None,
        credentials: CredentialsType = None,
        max_origins_per_page: Optional[int] = None,
        max_pages: Optional[int] = None,
        enable_origins: bool = True,
        incremental: bool = True,
    ):
        """Lister class for Maven repositories.

        Args:
            url: main URL of the Maven repository, i.e. url of the base index
                used to fetch maven artifacts. For Maven central use
                https://repo1.maven.org/maven2/
            index_url: the URL to download the exported text indexes from.
                Would typically be a local host running the export docker image.
                See README.md in this directory for more information.
            instance: Name of maven instance. Defaults to url's network location
                if unset.
            incremental: bool, defaults to True. Defines if incremental listing
                is activated or not.

        """
        self.BASE_URL = url
        self.INDEX_URL = index_url
        self.incremental = incremental

        super().__init__(
            scheduler=scheduler,
            credentials=credentials,
            url=url,
            instance=instance,
            with_github_session=True,
            max_origins_per_page=max_origins_per_page,
            max_pages=max_pages,
            enable_origins=enable_origins,
        )

        self.session.headers.update({"Accept": "application/json"})

        self.jar_origins: Dict[str, ListedOrigin] = {}

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

        # Download the main text index file.
        logger.info("Downloading computed index from %s.", self.INDEX_URL)
        assert self.INDEX_URL is not None
        try:
            response = self.http_request(self.INDEX_URL, stream=True)
        except requests.HTTPError:
            logger.error("Index %s not found, stopping", self.INDEX_URL)
            raise

        # Prepare regexes to parse index exports.

        # Parse doc id.
        # Example line: "doc 13"
        re_doc = re.compile(r"^doc (?P<doc>\d+)$")

        # Parse gid, aid, version, classifier, extension.
        # Example line: "    value al.aldi|sprova4j|0.1.0|sources|jar"
        re_val = re.compile(
            r"^\s{4}value (?P<gid>[^|]+)\|(?P<aid>[^|]+)\|(?P<version>[^|]+)\|"
            + r"(?P<classifier>[^|]+)\|(?P<ext>[^|]+)$"
        )

        # Parse last modification time.
        # Example line: "    value jar|1626109619335|14316|2|2|0|jar"
        re_time = re.compile(
            r"^\s{4}value ([^|]+)\|(?P<mtime>[^|]+)\|([^|]+)\|([^|]+)\|([^|]+)"
            + r"\|([^|]+)\|([^|]+)$"
        )

        # Read file line by line and process it
        out_pom: Dict = {}
        jar_src: Dict = {}
        doc_id: int = 0
        jar_src["doc"] = None
        url_src = None

        iterator = response.iter_lines(chunk_size=1024)
        for line_bytes in iterator:
            # Read the index text export and get URLs and SCMs.
            line = line_bytes.decode(errors="ignore")
            m_doc = re_doc.match(line)
            if m_doc is not None:
                doc_id = int(m_doc.group("doc"))
                # jar_src["doc"] contains the id of the current document, whatever
                # its type (scm or jar).
                jar_src["doc"] = doc_id
            else:
                m_val = re_val.match(line)
                if m_val is not None:
                    (gid, aid, version, classifier, ext) = m_val.groups()
                    ext = ext.strip()
                    path = "/".join(gid.split("."))
                    if classifier == "NA" and ext.lower() == "pom":
                        # If incremental mode, we don't record any line that is
                        # before our last recorded doc id.
                        if (
                            self.incremental
                            and self.state
                            and self.state.last_seen_pom
                            and self.state.last_seen_pom >= doc_id
                        ):
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
                        url_path = (
                            f"{path}/{aid}/{version}/{aid}-{version}-{classifier}.{ext}"
                        )
                        url_src = urljoin(self.BASE_URL, url_path)
                        jar_src["gid"] = gid
                        jar_src["aid"] = aid
                        jar_src["version"] = version
                else:
                    m_time = re_time.match(line)
                    if m_time is not None and url_src is not None:
                        time = m_time.group("mtime")
                        jar_src["time"] = int(time)
                        artifact_metadata_d = {
                            "type": "maven",
                            "url": url_src,
                            **jar_src,
                        }
                        logger.debug(
                            "* Yielding jar %s: %s", url_src, artifact_metadata_d
                        )
                        yield artifact_metadata_d
                        url_src = None

        logger.info("Found %s poms.", len(out_pom))

        # Now fetch pom files and scan them for scm info.
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
                    logger.debug("* Yielding pom %s: %s", pom_url, artifact_metadata_d)
                    yield artifact_metadata_d
                else:
                    logger.debug("No project.scm.connection in pom %s", pom_url)
            except requests.HTTPError:
                logger.warning(
                    "POM info page could not be fetched, skipping project '%s'",
                    pom_url,
                )
            except lxml.etree.Error as error:
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

        assert page["type"] == "scm"
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

        if url and visit_type == "git":
            assert self.github_session is not None
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
        if page["type"] == "scm":
            listed_origin = self.get_scm(page)
            if listed_origin:
                yield listed_origin
        else:
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

            if origin_url not in self.jar_origins:
                # Create ListedOrigin instance if we did not see that origin yet
                assert self.lister_obj.id is not None
                jar_origin = ListedOrigin(
                    lister_id=self.lister_obj.id,
                    url=origin_url,
                    visit_type=page["type"],
                    last_update=last_update_dt,
                    extra_loader_arguments={"artifacts": [artifact]},
                )
                self.jar_origins[origin_url] = jar_origin
            else:
                # Update list of source artifacts for that origin otherwise
                jar_origin = self.jar_origins[origin_url]
                artifacts = jar_origin.extra_loader_arguments["artifacts"]
                if artifact not in artifacts:
                    artifacts.append(artifact)

            if (
                jar_origin.last_update
                and last_update_dt
                and last_update_dt > jar_origin.last_update
            ):
                jar_origin.last_update = last_update_dt

            if not self.incremental or (
                self.state and page["doc"] > self.state.last_seen_doc
            ):
                # Yield origin with updated source artifacts, multiple instances of
                # ListedOrigin for the same origin URL but with different artifacts
                # list will be sent to the scheduler but it will deduplicate them and
                # take the latest one to upsert in database
                yield jar_origin

    def commit_page(self, page: RepoPage) -> None:
        """Update currently stored state using the latest listed doc.

        Note: this is a noop for full listing mode

        """
        if self.incremental and self.state:
            # We need to differentiate the two state counters according
            # to the type of origin.
            if page["type"] == "maven" and page["doc"] > self.state.last_seen_doc:
                self.state.last_seen_doc = page["doc"]
            elif page["type"] == "scm" and page["doc"] > self.state.last_seen_pom:
                self.state.last_seen_doc = page["doc"]
                self.state.last_seen_pom = page["doc"]

    def finalize(self) -> None:
        """Finalize the lister state, set update if any progress has been made.

        Note: this is a noop for full listing mode

        """
        if self.incremental and self.state:
            last_seen_doc = self.state.last_seen_doc
            last_seen_pom = self.state.last_seen_pom

            scheduler_state = self.get_state_from_scheduler()
            if last_seen_doc and last_seen_pom:
                if (scheduler_state.last_seen_doc < last_seen_doc) or (
                    scheduler_state.last_seen_pom < last_seen_pom
                ):
                    self.updated = True
