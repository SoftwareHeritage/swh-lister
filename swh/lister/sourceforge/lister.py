# Copyright (C) 2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from dataclasses import dataclass
from enum import Enum
import logging
import re
from typing import Iterator, List, Set
from xml.etree import ElementTree

import requests
from tenacity.before_sleep import before_sleep_log

from swh.lister.utils import throttling_retry
from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from .. import USER_AGENT
from ..pattern import CredentialsType, StatelessLister

logger = logging.getLogger(__name__)


class VcsNames(Enum):
    """Used to filter SourceForge tool names for valid VCS types"""

    CVS = "cvs"
    GIT = "git"
    SUBVERSION = "svn"
    MERCURIAL = "hg"
    BAZAAR = "bzr"


VCS_NAMES = set(VcsNames.__members__.values())


@dataclass
class SourceForgeListerEntry:
    vcs: VcsNames
    url: str


SourceForgeListerPage = List[SourceForgeListerEntry]

MAIN_SITEMAP_URL = "https://sourceforge.net/allura_sitemap/sitemap.xml"

# `namespace`: Project namespace. Very often `p`, but can be something else like
#              `adobe`
# `project`: Project name, e.g. `seedai`
PROJECT_REST_URL_FORMAT = "https://sourceforge.net/rest/{namespace}/{project}"

# `vcs`: VCS type, one of `VCS_NAMES`
# `namespace`: Project namespace. Very often `p`, but can be something else like
#              `adobe`
# `project`: Project name, e.g. `seedai`
# `mount_point`: url path used by the repo. For example, the Code::Blocks project
#                has `git` (https://git.code.sf.net/p/codeblocks/git)
CLONE_URL_FORMAT = "{vcs}.code.sf.net/{namespace}/{project}/{mount_point}"

PROJ_URL_RE = re.compile(
    r"^https://sourceforge.net/(?P<namespace>[^/]+)/(?P<project>[^/]+)"
)


class SourceForgeLister(StatelessLister[SourceForgeListerPage]):
    """List origins from the "SourceForge" forge.

    """

    # Part of the lister API, that identifies this lister
    LISTER_NAME = "sourceforge"

    def __init__(
        self,
        # Required
        scheduler: SchedulerInterface,
        # Instance URL, required for multi-instances listers (e.g gitlab, ...)
        url: str,
        # Instance name (free form) required for multi-instance listers,
        # or computed from `url`
        instance: str,
        # Required whether lister supports authentication or not
        credentials: CredentialsType = None,
    ):
        super().__init__(
            scheduler=scheduler, credentials=credentials, url=url, instance=instance,
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
        For each unique project page, we query a REST endpoint that lists (among
        other things) the tools associated with said project, some of which are
        the VCS used.
        Lastly we use the information of which VCS are used to build the predictable
        clone URL for any given VCS.
        """
        sitemap_contents = self.page_request(MAIN_SITEMAP_URL, {}).text
        tree = ElementTree.fromstring(sitemap_contents)

        # FIXME build an iterator to hide ugly XML manipulation
        for subsitemap in tree.iter("{*}sitemap"):
            # TODO use when adding incremental support
            # last_modified = sub_sitemap.find("{*}lastmod")
            location = subsitemap.find("{*}loc")
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
                last_update=None,
            )

    def _get_pages_from_subsitemap(self, subtree: ElementTree.Element):
        projects: Set[str] = set()
        for project_block in subtree.iter("{*}url"):
            # TODO use when adding incremental support
            # last_modified = project_block.find("{*}lastmod")
            location = project_block.find("{*}loc")
            assert location is not None
            project_url = location.text
            assert project_url is not None

            match = PROJ_URL_RE.match(project_url)
            if match:
                namespace = match.groupdict()["namespace"]
                if namespace == "projects":
                    # These have a `p`-namespaced counterpart, use that instead
                    continue

                project = match.groupdict()["project"]
                prev_len = len(projects)
                projects.add(project)

                if prev_len == len(project):
                    # Already seen
                    continue

                yield self._get_pages_for_project(namespace, project)
            else:
                # Should always match, let's log it
                msg = "Project URL '%s' does not match expected pattern"
                logger.warning(msg, project_url)

    def _get_pages_for_project(self, namespace, project) -> SourceForgeListerPage:
        endpoint = PROJECT_REST_URL_FORMAT.format(namespace=namespace, project=project)
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
            entry = SourceForgeListerEntry(vcs=VcsNames[tool_name], url=url)
            hits.append(entry)

        return hits
