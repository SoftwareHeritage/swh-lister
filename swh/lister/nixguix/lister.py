# Copyright (C) 2020-2023  The Software Heritage developers
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
import binascii
from dataclasses import dataclass
from enum import Enum
import logging
from pathlib import Path
import random
import re
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union
from urllib.parse import parse_qsl, urlparse

import requests
from requests.exceptions import ConnectionError, InvalidSchema, SSLError

from swh.core.tarball import MIMETYPE_TO_ARCHIVE_FORMAT
from swh.lister import TARBALL_EXTENSIONS
from swh.lister.pattern import CredentialsType, StatelessLister
from swh.scheduler.model import ListedOrigin

logger = logging.getLogger(__name__)


# By default, ignore binary files and archives containing binaries
DEFAULT_EXTENSIONS_TO_IGNORE = [
    "AppImage",
    "bin",
    "exe",
    "iso",
    "linux64",
    "msi",
    "png",
    "dic",
    "deb",
    "rpm",
]


class ArtifactNatureUndetected(ValueError):
    """Raised when a remote artifact's nature (tarball, file) cannot be detected."""

    pass


class ArtifactNatureMistyped(ValueError):
    """Raised when a remote artifact is neither a tarball nor a file.

    Error of this type are' probably a misconfiguration in the manifest generation that
    badly typed a vcs repository.

    """

    pass


class ArtifactWithoutExtension(ValueError):
    """Raised when an artifact nature cannot be determined by its name."""

    pass


class ChecksumLayout(Enum):
    """The possible artifact types listed out of the manifest."""

    STANDARD = "standard"
    """Standard "flat" checksums (e.g. sha1, sha256, ...) on the tarball or file."""
    NAR = "nar"
    """The checksum(s) are computed over the NAR dump of the output (e.g. uncompressed
    directory.). That uncompressed directory can come from a tarball or a (d)vcs. It's
    also called "recursive" in the "outputHashMode" key in the upstream dataset.

    """


MAPPING_CHECKSUM_LAYOUT = {
    "flat": ChecksumLayout.STANDARD,
    "recursive": ChecksumLayout.NAR,
}
"""Mapping between the outputHashMode from the manifest and how to compute checksums."""


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
    checksum_layout: ChecksumLayout
    """Checksum layout mode to provide to loaders (e.g. nar, standard, ...)"""
    ref: Optional[str]
    """Optional reference on the artifact (git commit, branch, svn commit, tag, ...)"""


@dataclass
class VCS:
    """Metadata information on VCS."""

    origin: str
    """Origin url of the vcs"""
    type: str
    """Type of (d)vcs, e.g. svn, git, hg, ..."""


class ArtifactType(Enum):
    """The possible artifact types listed out of the manifest."""

    ARTIFACT = "artifact"
    VCS = "vcs"


PageResult = Tuple[ArtifactType, Union[Artifact, VCS]]


VCS_SUPPORTED = ("git", "svn", "hg")

# Rough approximation of what we can find of mimetypes for tarballs "out there"
POSSIBLE_TARBALL_MIMETYPES = tuple(MIMETYPE_TO_ARCHIVE_FORMAT.keys())


PATTERN_VERSION = re.compile(r"(v*[0-9]+[.])([0-9]+[.]*)+")


def url_endswith(
    urlparsed, extensions: List[str], raise_when_no_extension: bool = True
) -> bool:
    """Determine whether urlparsed ends with one of the extensions passed as parameter.

    This also account for the edge case of a filename with only a version as name (so no
    extension in the end.)

    Raises:
        ArtifactWithoutExtension in case no extension is available and
        raise_when_no_extension is True (the default)

    """
    paths = [Path(p) for (_, p) in [("_", urlparsed.path)] + parse_qsl(urlparsed.query)]
    if raise_when_no_extension and not any(path.suffix != "" for path in paths):
        raise ArtifactWithoutExtension
    match = any(path.suffix.endswith(tuple(extensions)) for path in paths)
    if match:
        return match
    # Some false negative can happen (e.g. https://<netloc>/path/0.1.5)), so make sure
    # to catch those
    name = Path(urlparsed.path).name
    if not PATTERN_VERSION.match(name):
        return match
    if raise_when_no_extension:
        raise ArtifactWithoutExtension
    return False


def is_tarball(
    urls: List[str],
    request: Optional[Any] = None,
) -> Tuple[bool, str]:
    """Determine whether a list of files actually are tarball or simple files.

    This iterates over the list of urls provided to detect the artifact's nature. When
    this cannot be answered simply out of the url and ``request`` is provided, this
    executes a HTTP `HEAD` query on the url to determine the information. If request is
    not provided, this raises an ArtifactNatureUndetected exception.

    If, at the end of the iteration on the urls, no detection could be deduced, this
    raises an ArtifactNatureUndetected.

    Args:
        urls: name of the remote files to check for artifact nature.
        request: (Optional) Request object allowing http calls. If not provided and
            naive check cannot detect anything, this raises ArtifactNatureUndetected.

    Raises:
        ArtifactNatureUndetected when the artifact's nature cannot be detected out
            of its urls
        ArtifactNatureMistyped when the artifact is not a tarball nor a file. It's up to
            the caller to do what's right with it.

    Returns: A tuple (bool, url). The boolean represents whether the url is an archive
        or not. The second parameter is the actual url once the head request is issued
        as a fallback of not finding out whether the urls are tarballs or not.

    """

    def _is_tarball(url):
        """Determine out of an extension whether url is a tarball.

        Raises:
            ArtifactWithoutExtension in case no extension is available

        """
        urlparsed = urlparse(url)
        if urlparsed.scheme not in ("http", "https", "ftp"):
            raise ArtifactNatureMistyped(f"Mistyped artifact '{url}'")
        return url_endswith(urlparsed, TARBALL_EXTENSIONS)

    # Check all urls and as soon as an url allows the nature detection, this stops.
    exceptions_to_raise = []
    for url in urls:
        try:
            return _is_tarball(url), urls[0]
        except ArtifactWithoutExtension:
            if request is None:
                exc = ArtifactNatureUndetected(
                    f"Cannot determine artifact type from url <{url}>"
                )
                exceptions_to_raise.append(exc)
                continue

            logger.warning(
                "Cannot detect extension for <%s>. Fallback to http head query",
                url,
            )

            try:
                response = request.head(url)
            except (InvalidSchema, SSLError, ConnectionError):
                exc = ArtifactNatureUndetected(
                    f"Cannot determine artifact type from url <{url}>"
                )
                exceptions_to_raise.append(exc)
                continue

            if not response.ok or response.status_code == 404:
                exc = ArtifactNatureUndetected(
                    f"Cannot determine artifact type from url <{url}>"
                )
                exceptions_to_raise.append(exc)
                continue

            location = response.headers.get("Location")
            if location:  # It's not always present
                logger.debug("Location: %s", location)
                try:
                    # FIXME: location is also returned as it's considered the true
                    # origin, true enough?
                    return _is_tarball(location), location
                except ArtifactWithoutExtension:
                    logger.warning(
                        "Still cannot detect extension through location <%s>...",
                        url,
                    )

            origin = urls[0]

            content_type = response.headers.get("Content-Type")
            if content_type:
                logger.debug("Content-Type: %s", content_type)
                if content_type == "application/json":
                    return False, origin
                return content_type.startswith(POSSIBLE_TARBALL_MIMETYPES), origin

            content_disposition = response.headers.get("Content-Disposition")
            if content_disposition:
                logger.debug("Content-Disposition: %s", content_disposition)
                if "filename=" in content_disposition:
                    fields = content_disposition.split("; ")
                    for field in fields:
                        if "filename=" in field:
                            _, filename = field.split("filename=")
                            break

                    return (
                        url_endswith(
                            urlparse(filename),
                            TARBALL_EXTENSIONS,
                            raise_when_no_extension=False,
                        ),
                        origin,
                    )

    if len(exceptions_to_raise) > 0:
        raise exceptions_to_raise[0]
    raise ArtifactNatureUndetected(
        f"Cannot determine artifact type from url <{urls[0]}>"
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


VCS_ARTIFACT_TYPE_TO_VISIT_TYPE = {
    "git": "git-checkout",
    "hg": "hg-checkout",
    "svn": "svn-export",
}
"""Mapping between the vcs artifact type to the loader's visit type."""


class NixGuixLister(StatelessLister[PageResult]):
    """List Guix or Nix sources out of a public json manifest.

    This lister can output:
    - unique tarball (.tar.gz, .tbz2, ...)
    - vcs repositories (e.g. git, hg, svn)
    - unique file (.lisp, .py, ...)

    In the case of vcs repositories, if a reference is provided (``git_ref``,
    ``svn_revision`` or ``hg_changeset`` with a specific ``outputHashMode``
    ``recursive``), this provides one more origin to ingest as 'directory'. The
    DirectoryLoader will then be in charge to ingest the origin (checking the associated
    ``integrity`` field first).

    Note that, no `last_update` is available in either manifest (``guix`` or
    ``nixpkgs``), so listed_origins do not have it set.

    For `url` types artifacts, this tries to determine the artifact's nature, tarball or
    file. It first tries to compute out of the "url" extension. In case of no extension,
    it fallbacks to (HEAD) query the url to retrieve the origin out of the `Location`
    response header, and then checks the extension again.

    Optionally, when the `extension_to_ignore` parameter is provided, it extends the
    default extensions to ignore (`DEFAULT_EXTENSIONS_TO_IGNORE`) with those passed.
    This can be optionally used to filter some more binary files detected in the wild.

    """

    LISTER_NAME = "nixguix"

    def __init__(
        self,
        scheduler,
        url: str,
        origin_upstream: str,
        instance: Optional[str] = None,
        credentials: Optional[CredentialsType] = None,
        max_origins_per_page: Optional[int] = None,
        max_pages: Optional[int] = None,
        enable_origins: bool = True,
        # canonicalize urls, can be turned off during docker runs
        canonicalize: bool = True,
        extensions_to_ignore: List[str] = [],
        **kwargs: Any,
    ):
        super().__init__(
            scheduler=scheduler,
            url=url.rstrip("/"),
            instance=instance,
            credentials=credentials,
            with_github_session=canonicalize,
            max_origins_per_page=max_origins_per_page,
            max_pages=max_pages,
            enable_origins=enable_origins,
        )
        # either full fqdn NixOS/nixpkgs or guix repository urls
        # maybe add an assert on those specific urls?
        self.origin_upstream = origin_upstream
        self.extensions_to_ignore = DEFAULT_EXTENSIONS_TO_IGNORE + extensions_to_ignore

        self.session = requests.Session()

    def build_artifact(
        self, artifact_url: str, artifact_type: str
    ) -> Optional[Tuple[ArtifactType, VCS]]:
        """Build a canonicalized vcs artifact when possible."""
        origin = (
            self.github_session.get_canonical_url(artifact_url)
            if self.github_session
            else artifact_url
        )
        if not origin:
            return None
        return ArtifactType.VCS, VCS(origin=origin, type=artifact_type)

    def convert_integrity_to_checksums(
        self, integrity: str, failure_log: str
    ) -> Optional[Dict[str, str]]:
        """Determine the content checksum stored in the integrity field and convert
        into a dict of checksums. This only parses the `hash-expression`
        (hash-<b64-encoded-checksum>) as defined in
        https://w3c.github.io/webappsec-subresource-integrity/#the-integrity-attribute

        """
        try:
            chksum_algo, chksum_b64 = integrity.split("-")
            checksums: Dict[str, str] = {
                chksum_algo: base64.decodebytes(chksum_b64.encode()).hex()
            }
            return checksums
        except binascii.Error:
            logger.warning(failure_log)
            return None

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
                # This can output up to 2 origins of type
                # - vcs
                # - directory (with "nar" hashes)
                plain_url = artifact[VCS_KEYS_MAPPING[artifact_type]["url"]]
                built_artifact = self.build_artifact(plain_url, artifact_type)
                if not built_artifact:
                    continue
                yield built_artifact

                # Now, if we have also specific reference on the vcs, we want to ingest
                # a specific directory with nar hashes
                plain_ref = artifact.get(VCS_KEYS_MAPPING[artifact_type]["ref"])
                outputHashMode = artifact.get("outputHashMode", "flat")
                integrity = artifact.get("integrity")
                if plain_ref and integrity and outputHashMode == "recursive":
                    failure_log_if_any = (
                        f"Skipping url: <{plain_url}>: integrity computation failure "
                        f"for <{artifact}>"
                    )
                    checksums = self.convert_integrity_to_checksums(
                        integrity, failure_log=failure_log_if_any
                    )
                    if not checksums:
                        continue

                    yield ArtifactType.ARTIFACT, Artifact(
                        origin=plain_url,
                        fallback_urls=[],
                        checksums=checksums,
                        checksum_layout=MAPPING_CHECKSUM_LAYOUT[outputHashMode],
                        visit_type=VCS_ARTIFACT_TYPE_TO_VISIT_TYPE[artifact_type],
                        ref=plain_ref,
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
                    if urlparsed.scheme == "" and not re.match(r"^\w+@[^/]+:", url):
                        logger.warning("Missing scheme for <%s>: fallback to http", url)
                        fixed_url = f"http://{url}"
                    else:
                        fixed_url = url
                    urls.append(fixed_url)

                origin, *fallback_urls = urls

                if origin.endswith(".git"):
                    built_artifact = self.build_artifact(origin, "git")
                    if not built_artifact:
                        continue
                    yield built_artifact
                    continue

                outputHash = artifact.get("outputHash")
                integrity = artifact.get("integrity")
                if integrity is None and outputHash is None:
                    logger.warning(
                        "Skipping url <%s>: missing integrity and outputHash field",
                        origin,
                    )
                    continue

                # Falls back to outputHash field if integrity is missing
                if integrity is None and outputHash:
                    # We'll deal with outputHash as integrity field
                    integrity = outputHash

                # Checks urls for the artifact nature of the origin
                try:
                    is_tar, origin = is_tarball(urls, self.session)
                except ArtifactNatureMistyped:
                    logger.warning(
                        "Mistyped url <%s>: trying to deal with it properly", origin
                    )
                    urlparsed = urlparse(origin)
                    artifact_type = urlparsed.scheme

                    if artifact_type in VCS_SUPPORTED:
                        built_artifact = self.build_artifact(origin, artifact_type)
                        if not built_artifact:
                            continue
                        yield built_artifact
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

                failure_log_if_any = (
                    f"Skipping url: <{origin}>: integrity computation failure "
                    f"for <{artifact}>"
                )
                checksums = self.convert_integrity_to_checksums(
                    integrity, failure_log=failure_log_if_any
                )
                if not checksums:
                    continue

                # The 'outputHashMode' attribute determines how the hash is computed. It
                # must be one of the following two values:
                # - "flat": (default) The output must be a non-executable regular file.
                #     If it isn’t, the build fails. The hash is simply computed over the
                #     contents of that file (so it’s equal to what Unix commands like
                #     `sha256sum` or `sha1sum` produce).
                # - "recursive": The hash is computed over the NAR archive dump of the
                #       output (i.e., the result of `nix-store --dump`). In this case,
                #       the output can be anything, including a directory tree.
                outputHashMode = artifact.get("outputHashMode", "flat")
                if not is_tar and outputHashMode == "recursive":
                    # T4608: Cannot deal with those properly yet as some can be missing
                    # 'critical' information about how to recompute the hash (e.g. fs
                    # layout, executable bit, ...)
                    logger.warning(
                        "Skipping artifact <%s>: 'file' artifact of type <%s> is"
                        " missing information to properly check its integrity",
                        artifact,
                        artifact_type,
                    )
                    continue

                # At this point plenty of heuristics happened and we should have found
                # the right origin and its nature.

                # Let's check and filter it out if it is to be ignored (if possible).
                # Some origin urls may not have extension at this point (e.g
                # http://git.marmaro.de/?p=mmh;a=snp;h=<id>;sf=tgz), let them through.
                if url_endswith(
                    urlparse(origin),
                    self.extensions_to_ignore,
                    raise_when_no_extension=False,
                ):
                    logger.warning(
                        "Skipping artifact <%s>: 'file' artifact of type <%s> is"
                        " ignored due to lister configuration. It should ignore"
                        " origins with extension [%s]",
                        origin,
                        artifact_type,
                        ",".join(self.extensions_to_ignore),
                    )
                    continue

                logger.debug("%s: %s", "dir" if is_tar else "cnt", origin)
                yield ArtifactType.ARTIFACT, Artifact(
                    origin=origin,
                    fallback_urls=fallback_urls,
                    checksums=checksums,
                    checksum_layout=MAPPING_CHECKSUM_LAYOUT[outputHashMode],
                    visit_type="tarball-directory" if is_tar else "content",
                    ref=None,
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
        # Yield a vcs origin
        yield ListedOrigin(
            lister_id=self.lister_obj.id,
            url=artifact.origin,
            visit_type=artifact.type,
        )

    def artifact_to_listed_origin(self, artifact: Artifact) -> Iterator[ListedOrigin]:
        """Given an artifact (tarball, file), yield one ListedOrigin."""
        assert self.lister_obj.id is not None
        loader_arguments = {
            "checksums": artifact.checksums,
            "checksum_layout": artifact.checksum_layout.value,
            "fallback_urls": artifact.fallback_urls,
        }
        if artifact.ref:
            loader_arguments["ref"] = artifact.ref
        yield ListedOrigin(
            lister_id=self.lister_obj.id,
            url=artifact.origin,
            visit_type=artifact.visit_type,
            extra_loader_arguments=loader_arguments,
        )

    def get_origins_from_page(
        self, artifact_tuple: PageResult
    ) -> Iterator[ListedOrigin]:
        """Given an artifact tuple (type, artifact), yield a ListedOrigin."""
        artifact_type, artifact = artifact_tuple
        mapping_type_fn = getattr(self, f"{artifact_type.value}_to_listed_origin")
        yield from mapping_type_fn(artifact)
