# Copyright (C) 2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information
from dataclasses import dataclass
import datetime
from enum import Enum
import logging
import re
from typing import Iterator, List, Set
from xml.etree import ElementTree

import iso8601
import requests
from tenacity.before_sleep import before_sleep_log

from swh.lister.utils import throttling_retry
from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from .. import USER_AGENT
from ..pattern import StatelessLister

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
# `vcs`: VCS type, one of `VCS_NAMES`
# `namespace`: Project namespace. Very often `p`, but can be something else like
#              `adobe`.
# `project`: Project name, e.g. `seedai`. Can be a subproject, e.g `backapps/website`.
# `mount_point`: url path used by the repo. For example, the Code::Blocks project uses
#                `git` (https://git.code.sf.net/p/codeblocks/git).
CLONE_URL_FORMAT = "{vcs}.code.sf.net/{namespace}/{project}/{mount_point}"

PROJ_URL_RE = re.compile(
    r"^https://sourceforge.net/(?P<namespace>[^/]+)/(?P<project>[^/]+)/(?P<rest>.*)?"
)


class SourceForgeLister(StatelessLister[SourceForgeListerPage]):
    """List origins from the "SourceForge" forge.

    """

    # Part of the lister API, that identifies this lister
    LISTER_NAME = "sourceforge"

    def __init__(self, scheduler: SchedulerInterface):
        super().__init__(
            scheduler=scheduler, url="https://sourceforge.net", instance="main"
        )

        self.session = requests.Session()
        # Declare the USER_AGENT is more sysadm-friendly for the forge we list
        self.session.headers.update(
            {"Accept": "application/json", "User-Agent": USER_AGENT}
        )

    @throttling_retry(before_sleep=before_sleep_log(logger, logging.WARNING))
    def page_request(self, url, params) -> requests.Response:
        # Log listed URL to ease debugging
        logger.debug("Fetching URL %s with params %s", url, params)
        response = self.session.get(url, params=params)

        if response.status_code != 200:
            # Log response content to ease debugging
            logger.warning(
                "Unexpected HTTP status code %s on %s: %s",
                response.status_code,
                response.url,
                response.content,
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
            # TODO use when adding incremental support
            # last_modified = sub_sitemap.find(f"{SITEMAP_XML_NAMESPACE}lastmod")
            location = subsitemap.find(f"{SITEMAP_XML_NAMESPACE}loc")
            assert location is not None
            sub_url = location.text
            subsitemap_contents = self.page_request(sub_url, {}).text
            subtree = ElementTree.fromstring(subsitemap_contents)

            yield from self._get_pages_from_subsitemap(subtree)

    def get_origins_from_page(
        self, page: SourceForgeListerPage
    ) -> Iterator[ListedOrigin]:
        assert self.lister_obj.id is not None
        for hit in page:
            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                visit_type=hit.vcs.value,
                url=hit.url,
                last_update=iso8601.parse_date(hit.last_modified),
            )

    def _get_pages_from_subsitemap(
        self, subtree: ElementTree.Element
    ) -> Iterator[SourceForgeListerPage]:
        projects: Set[str] = set()
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
                # Should always match, let's log it
                msg = "Project URL '%s' does not match expected pattern"
                logger.warning(msg, project_url)

    def _get_pages_for_project(
        self, namespace, project, last_modified
    ) -> SourceForgeListerPage:
        endpoint = PROJECT_API_URL_FORMAT.format(namespace=namespace, project=project)
        res = self.page_request(endpoint, {}).json()

        tools = res.get("tools")
        if tools is None:
            # This probably never happens
            logger.warning("Project '%s' does not have any tools", endpoint)
            return []

        hits = []
        for tool in tools:
            tool_name = tool["name"]
            if tool_name not in VCS_NAMES:
                continue
            url = CLONE_URL_FORMAT.format(
                vcs=tool_name,
                namespace=namespace,
                project=project,
                mount_point=tool["mount_point"],
            )
            entry = SourceForgeListerEntry(
                vcs=VcsNames(tool_name), url=url, last_modified=last_modified
            )
            hits.append(entry)

        return hits
