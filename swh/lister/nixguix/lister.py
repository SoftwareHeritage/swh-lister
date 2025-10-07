# Copyright (C) 2020-2025  The Software Heritage developers
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
from datetime import datetime
import email.parser
import email.policy
from email.utils import parsedate_to_datetime
from enum import Enum
import logging
import random
import re
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union
from urllib.parse import urlparse

from swh.core.tarball import MIMETYPE_TO_ARCHIVE_FORMAT
from swh.lister import TARBALL_EXTENSIONS
from swh.lister.pattern import CredentialsType, StatelessLister
from swh.lister.utils import (
    ArtifactNatureMistyped,
    ArtifactNatureUndetected,
    is_tarball,
    url_contains_tarball_filename,
)
from swh.scheduler.model import ListedOrigin

logger = logging.getLogger(__name__)


# By default, ignore binary files and archives containing binaries
DEFAULT_EXTENSIONS_TO_IGNORE = [
    ".AppImage",
    ".bin",
    ".exe",
    ".iso",
    ".linux64",
    ".msi",
    ".png",
    ".dic",
    ".deb",
    ".rpm",
    ".nupkg",
]
"""By default, ignore binary files and archives containing binaries."""


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
    submodules: bool
    """Indicates if submodules should be retrieved for a git-checkout visit type"""
    svn_paths: Optional[List[str]]
    """Optional list of paths for the svn-export loader, only those will be exported
    and loaded into the archive"""
    extrinsic_metadata: Dict[str, Any]
    """Extrinsic metadata for the artifact as found in the JSON file consumed by the
    lister describing more precisely what is archived"""
    last_update: Optional[datetime]
    """"Optional last update date for the artifact"""


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

_narinfo_parser = email.parser.HeaderParser(policy=email.policy.strict)


def _parse_narinfo(narinfo: str) -> Dict[str, str]:
    return dict(_narinfo_parser.parsestr(narinfo))


class NixGuixLister(StatelessLister[PageResult]):
    """List Guix or Nix sources out of a public json manifest.

    This lister can output:

    * unique tarball URLs (.tar.gz, .tbz2, ...)
    * VCS repositories (e.g. git, hg, svn)
    * unique file URLs (.lisp, .py, ...)

    In the case of VCS repositories, if a reference is provided (``git_ref``,
    ``svn_revision`` or ``hg_changeset`` with a specific ``outputHashMode``
    set to ``recursive``), this provides one more origin to ingest as a directory.
    The :class:`swh.loader.git.directory.GitCheckoutLoader`,
    :class:`swh.loader.mercurial.directory.HgCheckoutLoader` and
    :class:`swh.loader.svn.directory.SvnExportLoader` classes will then be in
    charge to ingest the origin as a directory (checking the associated ``integrity``
    field first).

    Note that no ``last_update`` is available in ``guix`` manifest so listed origins
    do not have it set.

    For URL type artifacts, this tries to determine the artifact's nature, tarball or
    file. It first tries to compute out of the URL extension. In case of no extension,
    it fallbacks to ``HEAD`` query the URL to retrieve the origin out of the ``Location``
    response header, and then checks the extension again. As a last resort, a few bytes
    will be downloaded from the artifact URL to detect its nature from its mime type.
    The :class:`swh.loader.core.loader.ContentLoader` and
    :class:`swh.loader.core.loader.TarballDirectoryLoader` classes will then be
    in charge to ingest the origin (checking the associated ``integrity`` field
    first).

    Optionally, when the ``extension_to_ignore`` parameter is provided, it extends the
    default extensions to ignore (:const:`DEFAULT_EXTENSIONS_TO_IGNORE`) with those passed.
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
        nixos_cache_url: str = "https://cache.nixos.org",
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
        self.nixos_cache_url = nixos_cache_url

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

        sources = raw_data["sources"]
        random.shuffle(sources)

        for artifact in sources:
            artifact_type = artifact["type"]
            origin_urls = artifact.get("urls")
            outputHash = artifact.get("outputHash")
            outputHashMode = artifact.get("outputHashMode", "flat")
            integrity = artifact.get("integrity")

            if artifact_type == "url" and not origin_urls:
                # Nothing to fetch
                logger.warning("Skipping url <%s>: empty artifact", artifact)
                continue
            elif origin_urls:
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

                origin_urls = urls
                origin, *fallback_urls = urls

                # Let's check and filter it out if it is to be ignored (if possible).
                # Some origin urls may not have extension at this point (e.g
                # http://git.marmaro.de/?p=mmh;a=snp;h=<id>;sf=tgz), let them through.
                parsed_url = urlparse(origin)
                if artifact_type == "url" and (
                    url_contains_tarball_filename(
                        parsed_url,
                        self.extensions_to_ignore,
                        raise_when_no_extension=False,
                    )
                    # ignore nuget URLs as the archives contains binaries not source code
                    or parsed_url.netloc == "www.nuget.org"
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

                if integrity is None or not outputHashMode:
                    logger.warning(
                        "Skipping url <%s>: missing integrity or outputHashMode field",
                        origin,
                    )
                    continue
            elif artifact_type in ("git", "hg", "svn"):
                for vcs_url_field in ("git_url", "svn_url", "hg_url"):
                    if vcs_url_field in artifact:
                        origin = artifact[vcs_url_field]
                        origin_urls = [origin]
                        break
            else:
                logger.warning(
                    "Skipping artifact <%s>: unsupported type %s",
                    artifact,
                    artifact_type,
                )
                continue

            try:
                is_tar, origin = (
                    (True, origin)
                    if (artifact["type"] != "url" or outputHashMode == "recursive")
                    else is_tarball(origin_urls, self.session)
                )
            except ArtifactNatureUndetected:
                logger.warning(
                    "Skipping url <%s>: undetected remote artifact type",
                    artifact["urls"][0],
                )
                continue
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

            if "narinfo" in artifact:
                # special processing for NixOS packages if source code is available
                # for download from the nix remote HTTP cache

                # parse nar info, compute nar archive URL and execute heuristics
                # to determine source artifact type: tarball or regular file
                try:
                    narinfo = _parse_narinfo(artifact["narinfo"])
                except Exception:
                    # narinfo is not parsable, artifact cannot be fetched from nix cache
                    # so upstream content or tarball will be used instead
                    pass
                else:
                    artifact["narinfo"] = narinfo
                    origin = f"{self.nixos_cache_url}/{narinfo['URL']}"
                    if integrity is None or not outputHashMode:
                        logger.warning(
                            "Skipping url <%s>: missing integrity or outputHashMode field",
                            origin,
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
                    yield ArtifactType.ARTIFACT, Artifact(
                        origin=origin,
                        fallback_urls=[],
                        checksums=checksums,
                        checksum_layout=MAPPING_CHECKSUM_LAYOUT[outputHashMode],
                        visit_type="tarball-directory" if is_tar else "content",
                        ref=None,
                        submodules=False,
                        svn_paths=None,
                        extrinsic_metadata=artifact,
                        last_update=(
                            parsedate_to_datetime(artifact["last_modified"])
                            if "last_modified" in artifact
                            else None
                        ),
                    )
                    continue

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

                    origin_url = plain_url
                    svn_paths = artifact.get("svn_files")
                    if svn_paths:
                        # as multiple svn-export visit types can use the same base svn URL
                        # we modify the origin URL to ensure it is unique by appending the
                        # NAR hash value as a query parameter
                        origin_url += f"?nar={integrity}"

                    yield ArtifactType.ARTIFACT, Artifact(
                        origin=origin_url,
                        fallback_urls=[],
                        checksums=checksums,
                        checksum_layout=MAPPING_CHECKSUM_LAYOUT[outputHashMode],
                        visit_type=VCS_ARTIFACT_TYPE_TO_VISIT_TYPE[artifact_type],
                        ref=plain_ref,
                        submodules=artifact.get("submodule", False),
                        svn_paths=svn_paths,
                        extrinsic_metadata=artifact,
                        last_update=None,
                    )

            elif artifact_type == "url":

                if origin.endswith(".git"):
                    built_artifact = self.build_artifact(origin, "git")
                    if not built_artifact:
                        continue
                    yield built_artifact
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
                if (
                    not url_contains_tarball_filename(
                        parsed_url, TARBALL_EXTENSIONS, raise_when_no_extension=False
                    )
                    and outputHashMode == "recursive"
                ):
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

                logger.debug("%s: %s", "dir" if is_tar else "cnt", origin)
                yield ArtifactType.ARTIFACT, Artifact(
                    origin=origin,
                    fallback_urls=fallback_urls,
                    checksums=checksums,
                    checksum_layout=MAPPING_CHECKSUM_LAYOUT[outputHashMode],
                    visit_type="tarball-directory" if is_tar else "content",
                    ref=None,
                    submodules=False,
                    svn_paths=None,
                    extrinsic_metadata=artifact,
                    last_update=None,
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
        loader_arguments: Dict[str, Any] = {
            "checksums": artifact.checksums,
            "checksum_layout": artifact.checksum_layout.value,
            "fallback_urls": artifact.fallback_urls,
        }
        if artifact.ref:
            loader_arguments["ref"] = artifact.ref
        if artifact.submodules:
            loader_arguments["submodules"] = artifact.submodules
        if artifact.svn_paths:
            # extract the base svn url from the modified origin URL (see get_pages method)
            loader_arguments["svn_url"] = artifact.origin.rsplit("?", maxsplit=1)[0]
            loader_arguments["svn_paths"] = artifact.svn_paths
        if artifact.visit_type not in VCS_ARTIFACT_TYPE_TO_VISIT_TYPE.values():
            # only content and tarball-directory visit type support extrinsic_metadata parameter
            loader_arguments["extrinsic_metadata"] = artifact.extrinsic_metadata
        yield ListedOrigin(
            lister_id=self.lister_obj.id,
            url=artifact.origin,
            visit_type=artifact.visit_type,
            extra_loader_arguments=loader_arguments,
            last_update=artifact.last_update,
        )

    def get_origins_from_page(
        self, artifact_tuple: PageResult
    ) -> Iterator[ListedOrigin]:
        """Given an artifact tuple (type, artifact), yield a ListedOrigin."""
        artifact_type, artifact = artifact_tuple
        mapping_type_fn = getattr(self, f"{artifact_type.value}_to_listed_origin")
        yield from mapping_type_fn(artifact)
