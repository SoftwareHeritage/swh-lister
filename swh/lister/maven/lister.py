# Copyright (C) 2021 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import logging
import re
from typing import Any, Dict, Iterator, Optional
from urllib.parse import urljoin

import requests
from tenacity.before_sleep import before_sleep_log
from urllib3.util import parse_url
import xmltodict

from swh.lister.utils import throttling_retry
from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from .. import USER_AGENT
from ..pattern import CredentialsType, Lister

logger = logging.getLogger(__name__)

RepoPage = Dict[str, Any]


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
        index_url: str = None,
        instance: Optional[str] = None,
        credentials: CredentialsType = None,
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

        if instance is None:
            instance = parse_url(url).host

        super().__init__(
            scheduler=scheduler, credentials=credentials, url=url, instance=instance,
        )

        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/json", "User-Agent": USER_AGENT,}
        )

    def state_from_dict(self, d: Dict[str, Any]) -> MavenListerState:
        return MavenListerState(**d)

    def state_to_dict(self, state: MavenListerState) -> Dict[str, Any]:
        return asdict(state)

    @throttling_retry(before_sleep=before_sleep_log(logger, logging.WARNING))
    def page_request(self, url: str, params: Dict[str, Any]) -> requests.Response:

        logger.info("Fetching URL %s with params %s", url, params)

        response = self.session.get(url, params=params)
        if response.status_code != 200:
            logger.warning(
                "Unexpected HTTP status code %s on %s: %s",
                response.status_code,
                response.url,
                response.content,
            )
        response.raise_for_status()

        return response

    def get_pages(self) -> Iterator[RepoPage]:
        """ Retrieve and parse exported maven indexes to
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
        logger.info("Downloading text index from %s.", self.INDEX_URL)
        assert self.INDEX_URL is not None
        response = requests.get(self.INDEX_URL, stream=True)
        response.raise_for_status()

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
                if (
                    self.incremental
                    and self.state
                    and self.state.last_seen_doc
                    and self.state.last_seen_doc >= doc_id
                ):
                    # jar_src["doc"] contains the id of the current document, whatever
                    # its type (scm or jar).
                    jar_src["doc"] = None
                else:
                    jar_src["doc"] = doc_id
            else:
                # If incremental mode, we don't record any line that is
                # before our last recorded doc id.
                if self.incremental and jar_src["doc"] is None:
                    continue
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
                        url_pom = urljoin(self.BASE_URL, url_path,)
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

        logger.info("Fetching poms..")
        for pom in out_pom:
            text = self.page_request(pom, {})
            try:
                project = xmltodict.parse(text.content.decode())
                if "scm" in project["project"]:
                    if "connection" in project["project"]["scm"]:
                        scm = project["project"]["scm"]["connection"]
                        gid = project["project"]["groupId"]
                        aid = project["project"]["artifactId"]
                        artifact_metadata_d = {
                            "type": "scm",
                            "doc": out_pom[pom],
                            "url": scm,
                            "project": f"{gid}.{aid}",
                        }
                        logger.debug("* Yielding pom %s: %s", pom, artifact_metadata_d)
                        yield artifact_metadata_d
                    else:
                        logger.debug("No scm.connection in pom %s", pom)
                else:
                    logger.debug("No scm in pom %s", pom)
            except xmltodict.expat.ExpatError as error:
                logger.info("Could not parse POM %s XML: %s. Next.", pom, error)

    def get_origins_from_page(self, page: RepoPage) -> Iterator[ListedOrigin]:
        """Convert a page of Maven repositories into a list of ListedOrigins.

        """
        assert self.lister_obj.id is not None
        scm_types_ok = ("git", "svn", "hg", "cvs", "bzr")
        if page["type"] == "scm":
            # If origin is a scm url: detect scm type and yield.
            # Note that the official format is:
            # scm:git:git://github.com/openengsb/openengsb-framework.git
            # but many, many projects directly put the repo url, so we have to
            # detect the content to match it properly.
            m_scm = re.match(r"^scm:(?P<type>[^:]+):(?P<url>.*)$", page["url"])
            if m_scm is not None:
                scm_type = m_scm.group("type")
                if scm_type in scm_types_ok:
                    scm_url = m_scm.group("url")
                    origin = ListedOrigin(
                        lister_id=self.lister_obj.id, url=scm_url, visit_type=scm_type,
                    )
                    yield origin
            else:
                if page["url"].endswith(".git"):
                    origin = ListedOrigin(
                        lister_id=self.lister_obj.id, url=page["url"], visit_type="git",
                    )
                    yield origin
        else:
            # Origin is a source archive:
            last_update_dt = None
            last_update_iso = ""
            last_update_seconds = str(page["time"])[:-3]
            try:
                last_update_dt = datetime.fromtimestamp(int(last_update_seconds))
                last_update_dt_tz = last_update_dt.astimezone(timezone.utc)
            except OverflowError:
                logger.warning("- Failed to convert datetime %s.", last_update_seconds)
            if last_update_dt:
                last_update_iso = last_update_dt_tz.isoformat()
            origin = ListedOrigin(
                lister_id=self.lister_obj.id,
                url=page["url"],
                visit_type=page["type"],
                last_update=last_update_dt_tz,
                extra_loader_arguments={
                    "artifacts": [
                        {
                            "time": last_update_iso,
                            "gid": page["gid"],
                            "aid": page["aid"],
                            "version": page["version"],
                            "base_url": self.BASE_URL,
                        }
                    ]
                },
            )
            yield origin

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
