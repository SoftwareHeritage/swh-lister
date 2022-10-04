# Copyright (C) 2020-2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

"""NixGuix lister definition.

This lists artifacts out of manifest for Guix or Nixpkgs manifests.

Artifacts can be of types:
- upstream git repository (NixOS/nixpkgs, Guix)
- VCS repositories (svn, git, hg, ...)
- unique file
- unique tarball

"""

import base64
from dataclasses import dataclass
from enum import Enum
import logging
from pathlib import Path
import random
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union
from urllib.parse import urlparse

import requests
from requests.exceptions import ConnectionError, InvalidSchema, SSLError

from swh.core.github.utils import GitHubSession
from swh.core.tarball import MIMETYPE_TO_ARCHIVE_FORMAT
from swh.lister import TARBALL_EXTENSIONS
from swh.lister.pattern import CredentialsType, StatelessLister
from swh.scheduler.model import ListedOrigin

logger = logging.getLogger(__name__)


class ArtifactNatureUndetected(ValueError):
    """Raised when a remote artifact's nature (tarball, file) cannot be detected."""

    pass


class ArtifactNatureMistyped(ValueError):
    """Raised when a remote artifact's neither a tarball nor a file. It's probably a
    misconfiguration in the manifest that badly typed a vcs repository."""

    pass


@dataclass
class Artifact:
    """Metadata information on Remote Artifact with url (tarball or file)."""

    origin: str
    """Canonical url retrieve the tarball artifact."""
    visit_type: str
    """Either 'tar' or 'file' """
    fallback_urls: List[str]
    """List of urls to retrieve tarball artifact if canonical url no longer works."""
    checksums: Dict[str, str]
    """Integrity hash converted into a checksum dict."""


@dataclass
class VCS:
    """Metadata information on VCS."""

    origin: str
    """Origin url of the vcs"""
    type: str
    """Type of (d)vcs, e.g. svn, git, hg, ..."""
    ref: Optional[str] = None
    """Reference either a svn commit id, a git commit, ..."""


class ArtifactType(Enum):
    """The possible artifact types listed out of the manifest."""

    ARTIFACT = "artifact"
    VCS = "vcs"


PageResult = Tuple[ArtifactType, Union[Artifact, VCS]]


VCS_SUPPORTED = ("git", "svn", "hg")

# Rough approximation of what we can find of mimetypes for tarballs "out there"
POSSIBLE_TARBALL_MIMETYPES = set(MIMETYPE_TO_ARCHIVE_FORMAT.keys())


def is_tarball(urls: List[str], request: Optional[Any] = None) -> Tuple[bool, str]:
    """Determine whether a list of files actually are tarballs or simple files.

    When this cannot be answered simply out of the url, when request is provided, this
    executes a HTTP `HEAD` query on the url to determine the information. If request is
    not provided, this raises an ArtifactNatureUndetected exception.

    Args:
        urls: name of the remote files for which the extension needs to be checked.

    Raises:
        ArtifactNatureUndetected when the artifact's nature cannot be detected out
            of its url
        ArtifactNatureMistyped when the artifact is not a tarball nor a file. It's up to
            the caller to do what's right with it.

    Returns: A tuple (bool, url). The boolean represents whether the url is an archive
        or not. The second parameter is the actual url once the head request is issued
        as a fallback of not finding out whether the urls are tarballs or not.

    """

    def _is_tarball(url):
        """Determine out of an extension whether url is a tarball.

        Raises:
            IndexError in case no extension is available

        """
        urlparsed = urlparse(url)
        if urlparsed.scheme not in ("http", "https", "ftp"):
            raise ArtifactNatureMistyped(f"Mistyped artifact '{url}'")
        return Path(urlparsed.path).suffixes[-1].lstrip(".") in TARBALL_EXTENSIONS

    index = random.randrange(len(urls))
    url = urls[index]

    try:
        return _is_tarball(url), urls[0]
    except IndexError:
        if request is None:
            raise ArtifactNatureUndetected(
                f"Cannot determine artifact type from url <{url}>"
            )
        logger.warning(
            "Cannot detect extension for <%s>. Fallback to http head query",
            url,
        )

        try:
            response = request.head(url)
        except (InvalidSchema, SSLError, ConnectionError):
            raise ArtifactNatureUndetected(
                f"Cannot determine artifact type from url <{url}>"
            )

        if not response.ok or response.status_code == 404:
            raise ArtifactNatureUndetected(
                f"Cannot determine artifact type from url <{url}>"
            )
        location = response.headers.get("Location")
        if location:  # It's not always present
            logger.debug("Location: %s", location)
            try:
                # FIXME: location is also returned as it's considered the true origin,
                # true enough?
                return _is_tarball(location), location
            except IndexError:
                logger.warning(
                    "Still cannot detect extension through location <%s>...",
                    url,
                )

        content_type = response.headers.get("Content-Type")
        if content_type:
            logger.debug("Content-Type: %s", content_type)
            if content_type == "application/json":
                return False, urls[0]
            return content_type in POSSIBLE_TARBALL_MIMETYPES, urls[0]

        raise ArtifactNatureUndetected(
            f"Cannot determine artifact type from url <{url}>"
        )


VCS_KEYS_MAPPING = {
    "git": {
        "ref": "git_ref",
        "url": "git_url",
    },
    "svn": {
        "ref": "svn_revision",
        "url": "svn_url",
    },
    "hg": {
        "ref": "hg_changeset",
        "url": "hg_url",
    },
}


class NixGuixLister(StatelessLister[PageResult]):
    """List Guix or Nix sources out of a public json manifest.

    This lister can output:
    - unique tarball (.tar.gz, .tbz2, ...)
    - vcs repositories (e.g. git, hg, svn)
    - unique file (.lisp, .py, ...)

    Note that no `last_update` is available in either manifest.

    For `url` types artifacts, this tries to determine the artifact's nature, tarball or
    file. It first tries to compute out of the "url" extension. In case of no extension,
    it fallbacks to query (HEAD) the url to retrieve the origin out of the `Location`
    response header, and then checks the extension again.

    """

    LISTER_NAME = "nixguix"

    def __init__(
        self,
        scheduler,
        url: str,
        origin_upstream: str,
        instance: Optional[str] = None,
        credentials: Optional[CredentialsType] = None,
        # canonicalize urls, can be turned off during docker runs
        canonicalize: bool = True,
        **kwargs: Any,
    ):
        super().__init__(
            scheduler=scheduler,
            url=url.rstrip("/"),
            instance=instance,
            credentials=credentials,
        )
        # either full fqdn NixOS/nixpkgs or guix repository urls
        # maybe add an assert on those specific urls?
        self.origin_upstream = origin_upstream

        self.session = requests.Session()
        # for testing purposes, we may want to skip this step (e.g. docker run and rate
        # limit)
        self.github_session = (
            GitHubSession(
                credentials=self.credentials,
                user_agent=str(self.session.headers["User-Agent"]),
            )
            if canonicalize
            else None
        )

    def get_pages(self) -> Iterator[PageResult]:
        """Yield one page per "typed" origin referenced in manifest."""
        # fetch and parse the manifest...
        response = self.http_request(self.url)

        # ... if any
        raw_data = response.json()
        yield ArtifactType.VCS, VCS(origin=self.origin_upstream, type="git")

        # grep '"type"' guix-sources.json | sort | uniq
        #       "type": false                             <<<<<<<<< noise
        #       "type": "git",
        #       "type": "hg",
        #       "type": "no-origin",                      <<<<<<<<< noise
        #       "type": "svn",
        #       "type": "url",

        # grep '"type"' nixpkgs-sources-unstable.json | sort | uniq
        #  "type": "url",

        sources = raw_data["sources"]
        random.shuffle(sources)

        for artifact in sources:
            artifact_type = artifact["type"]
            if artifact_type in VCS_SUPPORTED:
                plain_url = artifact[VCS_KEYS_MAPPING[artifact_type]["url"]]
                plain_ref = artifact[VCS_KEYS_MAPPING[artifact_type]["ref"]]
                artifact_url = (
                    self.github_session.get_canonical_url(plain_url)
                    if self.github_session
                    else plain_url
                )
                if not artifact_url:
                    continue
                yield ArtifactType.VCS, VCS(
                    origin=artifact_url, type=artifact_type, ref=plain_ref
                )
            elif artifact_type == "url":
                # It's either a tarball or a file
                origin_urls = artifact.get("urls")
                if not origin_urls:
                    # Nothing to fetch
                    logger.warning("Skipping url <%s>: empty artifact", artifact)
                    continue

                assert origin_urls is not None

                # Deal with urls with empty scheme (basic fallback to http)
                urls = []
                for url in origin_urls:
                    urlparsed = urlparse(url)
                    if urlparsed.scheme == "":
                        logger.warning("Missing scheme for <%s>, fallback to http", url)
                        fixed_url = f"http://{url}"
                    else:
                        fixed_url = url
                    urls.append(fixed_url)

                origin, *fallback_urls = urls

                integrity = artifact.get("integrity")
                if integrity is None:
                    logger.warning("Skipping url <%s>: missing integrity field", origin)
                    continue

                try:
                    is_tar, origin = is_tarball(urls, self.session)
                except ArtifactNatureMistyped:
                    logger.warning(
                        "Mistyped url <%s>: trying to deal with it properly", origin
                    )
                    urlparsed = urlparse(origin)
                    artifact_type = urlparsed.scheme
                    if artifact_type in VCS_SUPPORTED:
                        artifact_url = (
                            self.github_session.get_canonical_url(origin)
                            if self.github_session
                            else origin
                        )
                        if not artifact_url:
                            continue
                        yield ArtifactType.VCS, VCS(
                            origin=artifact_url, type=artifact_type
                        )
                    else:
                        logger.warning(
                            "Skipping url <%s>: undetected remote artifact type", origin
                        )
                    continue
                except ArtifactNatureUndetected:
                    logger.warning(
                        "Skipping url <%s>: undetected remote artifact type", origin
                    )
                    continue

                # Determine the content checksum stored in the integrity field and
                # convert into a dict of checksums. This only parses the
                # `hash-expression` (hash-<b64-encoded-checksum>) as defined in
                # https://w3c.github.io/webappsec-subresource-integrity/#the-integrity-attribute
                chksum_algo, chksum_b64 = integrity.split("-")
                checksums: Dict[str, str] = {
                    chksum_algo: base64.decodebytes(chksum_b64.encode()).hex()
                }

                logger.debug("%s: %s", "dir" if is_tar else "cnt", origin)
                yield ArtifactType.ARTIFACT, Artifact(
                    origin=origin,
                    fallback_urls=fallback_urls,
                    checksums=checksums,
                    visit_type="directory" if is_tar else "content",
                )
            else:
                logger.warning(
                    "Skipping artifact <%s>: unsupported type %s",
                    artifact,
                    artifact_type,
                )

    def vcs_to_listed_origin(self, artifact: VCS) -> Iterator[ListedOrigin]:
        """Given a vcs repository, yield a ListedOrigin."""
        assert self.lister_obj.id is not None
        # FIXME: What to do with the "ref" (e.g. git/hg/svn commit, ...)
        yield ListedOrigin(
            lister_id=self.lister_obj.id,
            url=artifact.origin,
            visit_type=artifact.type,
        )

    def artifact_to_listed_origin(self, artifact: Artifact) -> Iterator[ListedOrigin]:
        """Given an artifact (tarball, file), yield one ListedOrigin."""
        assert self.lister_obj.id is not None
        yield ListedOrigin(
            lister_id=self.lister_obj.id,
            url=artifact.origin,
            visit_type=artifact.visit_type,
            extra_loader_arguments={
                "checksums": artifact.checksums,
                "fallback_urls": artifact.fallback_urls,
            },
        )

    def get_origins_from_page(
        self, artifact_tuple: PageResult
    ) -> Iterator[ListedOrigin]:
        """Given an artifact tuple (type, artifact), yield a ListedOrigin."""
        artifact_type, artifact = artifact_tuple
        mapping_type_fn = getattr(self, f"{artifact_type.value}_to_listed_origin")
        yield from mapping_type_fn(artifact)
