# Copyright (C) 2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information
from dataclasses import dataclass, field
import datetime
from enum import Enum
import logging
import re
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple
from xml.etree import ElementTree

from bs4 import BeautifulSoup
import iso8601
import requests
from tenacity.before_sleep import before_sleep_log

from swh.core.api.classes import stream_results
from swh.lister.utils import retry_policy_generic, throttling_retry
from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from .. import USER_AGENT
from ..pattern import CredentialsType, Lister

logger = logging.getLogger(__name__)


class VcsNames(Enum):
    """Used to filter SourceForge tool names for valid VCS types"""

    # CVS projects are read-only
    CVS = "cvs"
    GIT = "git"
    SUBVERSION = "svn"
    MERCURIAL = "hg"
    BAZAAR = "bzr"


VCS_NAMES = set(v.value for v in VcsNames.__members__.values())


@dataclass
class SourceForgeListerEntry:
    vcs: VcsNames
    url: str
    last_modified: datetime.date


SubSitemapNameT = str
ProjectNameT = str
# SourceForge only offers day-level granularity, which is good enough for our purposes
LastModifiedT = datetime.date


@dataclass
class SourceForgeListerState:
    """Current state of the SourceForge lister in incremental runs
    """

    """If the subsitemap does not exist, we assume a full run of this subsitemap
    is needed. If the date is the same, we skip the subsitemap, otherwise we
    request the subsitemap and look up every project's "last modified" date
    to compare against `ListedOrigins` from the database."""
    subsitemap_last_modified: Dict[SubSitemapNameT, LastModifiedT] = field(
        default_factory=dict
    )
    """Some projects (not the majority, but still meaningful) have no VCS for us to
    archive. We need to remember a mapping of their API URL to their "last modified"
    date so we don't keep querying them needlessly every time."""
    empty_projects: Dict[str, LastModifiedT] = field(default_factory=dict)


SourceForgeListerPage = List[SourceForgeListerEntry]

MAIN_SITEMAP_URL = "https://sourceforge.net/allura_sitemap/sitemap.xml"
SITEMAP_XML_NAMESPACE = "{http://www.sitemaps.org/schemas/sitemap/0.9}"

# API resource endpoint for information about the given project.
#
# `namespace`: Project namespace. Very often `p`, but can be something else like
#              `adobe`
# `project`: Project name, e.g. `seedai`. Can be a subproject, e.g `backapps/website`.
PROJECT_API_URL_FORMAT = "https://sourceforge.net/rest/{namespace}/{project}"

# Predictable URL for cloning (in the broad sense) a VCS registered for the project.
#
# Warning: does not apply to bzr repos, and Mercurial are http only, see use of this
# constant below.
#
# `vcs`: VCS type, one of `VCS_NAMES`
# `namespace`: Project namespace. Very often `p`, but can be something else like
#              `adobe`.
# `project`: Project name, e.g. `seedai`. Can be a subproject, e.g `backapps/website`.
# `mount_point`: url path used by the repo. For example, the Code::Blocks project uses
#                `git` (https://git.code.sf.net/p/codeblocks/git).
CLONE_URL_FORMAT = "https://{vcs}.code.sf.net/{namespace}/{project}/{mount_point}"

PROJ_URL_RE = re.compile(
    r"^https://sourceforge.net/(?P<namespace>[^/]+)/(?P<project>[^/]+)/(?P<rest>.*)?"
)

# Mapping of `(namespace, project name)` to `last modified` date.
ProjectsLastModifiedCache = Dict[Tuple[str, str], LastModifiedT]


class SourceForgeLister(Lister[SourceForgeListerState, SourceForgeListerPage]):
    """List origins from the "SourceForge" forge.

    """

    # Part of the lister API, that identifies this lister
    LISTER_NAME = "sourceforge"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        incremental: bool = False,
        credentials: Optional[CredentialsType] = None,
    ):
        super().__init__(
            scheduler=scheduler,
            url="https://sourceforge.net",
            instance="main",
            credentials=credentials,
        )

        # Will hold the currently saved "last modified" dates to compare against our
        # requests.
        self._project_last_modified: Optional[ProjectsLastModifiedCache] = None
        self.session = requests.Session()
        # Declare the USER_AGENT is more sysadm-friendly for the forge we list
        self.session.headers.update(
            {"Accept": "application/json", "User-Agent": USER_AGENT}
        )
        self.incremental = incremental

    def state_from_dict(self, d: Dict[str, Dict[str, Any]]) -> SourceForgeListerState:
        subsitemaps = {
            k: datetime.date.fromisoformat(v)
            for k, v in d.get("subsitemap_last_modified", {}).items()
        }
        empty_projects = {
            k: datetime.date.fromisoformat(v)
            for k, v in d.get("empty_projects", {}).items()
        }
        return SourceForgeListerState(
            subsitemap_last_modified=subsitemaps, empty_projects=empty_projects
        )

    def state_to_dict(self, state: SourceForgeListerState) -> Dict[str, Any]:
        return {
            "subsitemap_last_modified": {
                k: v.isoformat() for k, v in state.subsitemap_last_modified.items()
            },
            "empty_projects": {
                k: v.isoformat() for k, v in state.empty_projects.items()
            },
        }

    def projects_last_modified(self) -> ProjectsLastModifiedCache:
        if not self.incremental:
            # No point in loading the previous results if we're doing a full run
            return {}
        if self._project_last_modified is not None:
            return self._project_last_modified
        # We know there will be at least that many origins
        stream = stream_results(
            self.scheduler.get_listed_origins, self.lister_obj.id, limit=300_000
        )
        listed_origins = dict()
        # Projects can have slashes in them if they're subprojects, but the
        # mointpoint (last component) cannot.
        url_match = re.compile(
            r".*\.code\.sf\.net/(?P<namespace>[^/]+)/(?P<project>.+)/.*"
        )
        bzr_url_match = re.compile(
            r"http://(?P<project>[^/]+).bzr.sourceforge.net/bzrroot/([^/]+)"
        )
        cvs_url_match = re.compile(
            r"rsync://a.cvs.sourceforge.net/cvsroot/(?P<project>.+)/([^/]+)"
        )

        for origin in stream:
            url = origin.url
            match = url_match.match(url)
            if match is None:
                # Could be a bzr or cvs special endpoint
                bzr_match = bzr_url_match.match(url)
                cvs_match = cvs_url_match.match(url)
                matches = None
                if bzr_match is not None:
                    matches = bzr_match.groupdict()
                elif cvs_match is not None:
                    matches = cvs_match.groupdict()
                assert matches
                project = matches["project"]
                namespace = "p"  # no special namespacing for bzr and cvs projects
            else:
                matches = match.groupdict()
                namespace = matches["namespace"]
                project = matches["project"]
            # "Last modified" dates are the same across all VCS (tools, even)
            # within a project or subproject. An assertion here would be overkill.
            last_modified = origin.last_update
            assert last_modified is not None
            listed_origins[(namespace, project)] = last_modified.date()

        self._project_last_modified = listed_origins
        return listed_origins

    @throttling_retry(
        retry=retry_policy_generic,
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def page_request(self, url, params) -> requests.Response:
        # Log listed URL to ease debugging
        logger.debug("Fetching URL %s with params %s", url, params)
        response = self.session.get(url, params=params)

        if response.status_code != 200:
            # Log response content to ease debugging
            logger.warning(
                "Unexpected HTTP status code %s for URL %s",
                response.status_code,
                response.url,
            )
        # The lister must fail on blocking errors
        response.raise_for_status()

        return response

    def get_pages(self) -> Iterator[SourceForgeListerPage]:
        """
        SourceForge has a main XML sitemap that lists its sharded sitemaps for all
        projects.
        Each XML sub-sitemap lists project pages, which are not unique per project: a
        project can have a wiki, a home, a git, an svn, etc.
        For each unique project, we query an API endpoint that lists (among
        other things) the tools associated with said project, some of which are
        the VCS used. Subprojects are considered separate projects.
        Lastly we use the information of which VCS are used to build the predictable
        clone URL for any given VCS.
        """
        sitemap_contents = self.page_request(MAIN_SITEMAP_URL, {}).text
        tree = ElementTree.fromstring(sitemap_contents)

        for subsitemap in tree.iterfind(f"{SITEMAP_XML_NAMESPACE}sitemap"):
            last_modified_el = subsitemap.find(f"{SITEMAP_XML_NAMESPACE}lastmod")
            assert last_modified_el is not None and last_modified_el.text is not None
            last_modified = datetime.date.fromisoformat(last_modified_el.text)
            location = subsitemap.find(f"{SITEMAP_XML_NAMESPACE}loc")
            assert location is not None and location.text is not None
            sub_url = location.text

            if self.incremental:
                recorded_last_mod = self.state.subsitemap_last_modified.get(sub_url)
                if recorded_last_mod == last_modified:
                    # The entire subsitemap hasn't changed, so none of its projects
                    # have either, skip it.
                    continue

            self.state.subsitemap_last_modified[sub_url] = last_modified
            subsitemap_contents = self.page_request(sub_url, {}).text
            subtree = ElementTree.fromstring(subsitemap_contents)

            yield from self._get_pages_from_subsitemap(subtree)

    def get_origins_from_page(
        self, page: SourceForgeListerPage
    ) -> Iterator[ListedOrigin]:
        assert self.lister_obj.id is not None
        for hit in page:
            last_modified: str = str(hit.last_modified)
            last_update: datetime.datetime = iso8601.parse_date(last_modified)
            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                visit_type=hit.vcs.value,
                url=hit.url,
                last_update=last_update,
            )

    def _get_pages_from_subsitemap(
        self, subtree: ElementTree.Element
    ) -> Iterator[SourceForgeListerPage]:
        projects: Set[ProjectNameT] = set()
        for project_block in subtree.iterfind(f"{SITEMAP_XML_NAMESPACE}url"):
            last_modified_block = project_block.find(f"{SITEMAP_XML_NAMESPACE}lastmod")
            assert last_modified_block is not None
            last_modified = last_modified_block.text
            location = project_block.find(f"{SITEMAP_XML_NAMESPACE}loc")
            assert location is not None
            project_url = location.text
            assert project_url is not None

            match = PROJ_URL_RE.match(project_url)
            if match:
                matches = match.groupdict()
                namespace = matches["namespace"]
                if namespace == "projects":
                    # These have a `p`-namespaced counterpart, use that instead
                    continue

                project = matches["project"]
                rest = matches["rest"]
                if rest.count("/") > 1:
                    # This is a subproject. There exists no sub-subprojects.
                    subproject_name = rest.rsplit("/", 2)[0]
                    project = f"{project}/{subproject_name}"

                prev_len = len(projects)
                projects.add(project)

                if prev_len == len(projects):
                    # Already seen
                    continue

                pages = self._get_pages_for_project(namespace, project, last_modified)
                if pages:
                    yield pages
                else:
                    logger.debug("Project '%s' does not have any VCS", project)
            else:
                # Should almost always match, let's log it
                # The only ones that don't match are mostly specialized one-off URLs.
                msg = "Project URL '%s' does not match expected pattern"
                logger.warning(msg, project_url)

    def _get_pages_for_project(
        self, namespace, project, last_modified
    ) -> SourceForgeListerPage:
        endpoint = PROJECT_API_URL_FORMAT.format(namespace=namespace, project=project)
        empty_project_last_modified = self.state.empty_projects.get(endpoint)
        if empty_project_last_modified is not None:
            if last_modified == empty_project_last_modified.isoformat():
                # Project has not changed, so is still empty, meaning it has
                # no VCS attached that we can archive.
                logger.debug(f"Project {namespace}/{project} is still empty")
                return []

        if self.incremental:
            expected = self.projects_last_modified().get((namespace, project))

            if expected is not None:
                if expected.isoformat() == last_modified:
                    # Project has not changed
                    logger.debug(f"Project {namespace}/{project} has not changed")
                    return []
                else:
                    logger.debug(f"Project {namespace}/{project} was updated")
            else:
                msg = "New project during an incremental run: %s/%s"
                logger.debug(msg, namespace, project)

        try:
            res = self.page_request(endpoint, {}).json()
        except requests.HTTPError:
            # We've already logged in `page_request`
            return []

        tools = res.get("tools")
        if tools is None:
            # This rarely happens, on very old URLs
            logger.warning("Project '%s' does not have any tools", endpoint)
            return []

        hits = []
        for tool in tools:
            tool_name = tool["name"]
            if tool_name not in VCS_NAMES:
                continue
            if tool_name == VcsNames.CVS.value:
                # CVS projects are different from other VCS ones, they use the rsync
                # protocol, a list of modules needs to be fetched from an info page
                # and multiple origin URLs can be produced for a same project.
                cvs_info_url = f"http://{project}.cvs.sourceforge.net"
                try:
                    response = self.page_request(cvs_info_url, params={})
                except requests.HTTPError:
                    logger.warning(
                        "CVS info page could not be fetched, skipping project '%s'",
                        project,
                    )
                    continue
                else:
                    bs = BeautifulSoup(response.text, features="html.parser")
                    cvs_base_url = "rsync://a.cvs.sourceforge.net/cvsroot"
                    for text in [b.text for b in bs.find_all("b")]:
                        match = re.search(fr".*/cvsroot/{project} co -P (.+)", text)
                        if match is not None:
                            module = match.group(1)
                            url = f"{cvs_base_url}/{project}/{module}"
                            hits.append(
                                SourceForgeListerEntry(
                                    vcs=VcsNames(tool_name),
                                    url=url,
                                    last_modified=last_modified,
                                )
                            )
                    continue
            url = CLONE_URL_FORMAT.format(
                vcs=tool_name,
                namespace=namespace,
                project=project,
                mount_point=tool["mount_point"],
            )
            if tool_name == VcsNames.MERCURIAL.value:
                # SourceForge does not yet support anonymous HTTPS cloning for Mercurial
                # See https://sourceforge.net/p/forge/feature-requests/727/
                url = url.replace("https://", "http://")
            if tool_name == VcsNames.BAZAAR.value:
                # SourceForge has removed support for bzr and only keeps legacy projects
                # around at a separate (also not https) URL. Bzr projects are very rare
                # and a lot of them are 404 now.
                url = f"http://{project}.bzr.sourceforge.net/bzrroot/{project}"
            entry = SourceForgeListerEntry(
                vcs=VcsNames(tool_name), url=url, last_modified=last_modified
            )
            hits.append(entry)

        if not hits:
            date = datetime.date.fromisoformat(last_modified)
            self.state.empty_projects[endpoint] = date
        else:
            self.state.empty_projects.pop(endpoint, None)

        return hits
