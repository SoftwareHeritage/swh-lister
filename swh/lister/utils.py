# Copyright (C) 2018-2024 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


import logging
from pathlib import Path
import re
from typing import Any, Iterator, List, Optional, Tuple
from urllib.parse import parse_qsl, urlparse

from requests.exceptions import ConnectionError, InvalidSchema, SSLError

from swh.core.tarball import MIMETYPE_TO_ARCHIVE_FORMAT
from swh.lister import TARBALL_EXTENSIONS

logger = logging.getLogger(__name__)


def split_range(total_pages: int, nb_pages: int) -> Iterator[Tuple[int, int]]:
    """Split `total_pages` into mostly `nb_pages` ranges. In some cases, the last range can
    have one more element.

    >>> list(split_range(19, 10))
    [(0, 9), (10, 19)]

    >>> list(split_range(20, 3))
    [(0, 2), (3, 5), (6, 8), (9, 11), (12, 14), (15, 17), (18, 20)]

    >>> list(split_range(21, 3))
    [(0, 2), (3, 5), (6, 8), (9, 11), (12, 14), (15, 17), (18, 21)]

    """
    prev_index = None
    for index in range(0, total_pages, nb_pages):
        if index is not None and prev_index is not None:
            yield prev_index, index - 1
        prev_index = index

    if index != total_pages:
        yield index, total_pages


def is_valid_origin_url(url: Optional[str]) -> bool:
    """Returns whether the given string is a valid origin URL.
    This excludes Git SSH URLs and pseudo-URLs (eg. ``ssh://git@example.org:foo``
    and ``git@example.org:foo``), as they are not supported by the Git loader
    and usually require authentication.

    All HTTP URLs are allowed:

    >>> is_valid_origin_url("http://example.org/repo.git")
    True
    >>> is_valid_origin_url("http://example.org/repo")
    True
    >>> is_valid_origin_url("https://example.org/repo")
    True
    >>> is_valid_origin_url("https://foo:bar@example.org/repo")
    True

    Scheme-less URLs are rejected;

    >>> is_valid_origin_url("example.org/repo")
    False
    >>> is_valid_origin_url("example.org:repo")
    False

    Git SSH URLs and pseudo-URLs are rejected:

    >>> is_valid_origin_url("git@example.org:repo")
    False
    >>> is_valid_origin_url("ssh://git@example.org:repo")
    False
    """
    if not url:
        # Empty or None
        return False

    parsed = urlparse(url)
    if not parsed.netloc:
        # Is parsed as a relative URL
        return False

    if parsed.scheme == "ssh":
        # Git SSH URL
        return False

    return True


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


# Rough approximation of what we can find of mimetypes for tarballs "out there"
POSSIBLE_TARBALL_MIMETYPES = tuple(MIMETYPE_TO_ARCHIVE_FORMAT.keys())


PATTERN_VERSION = re.compile(r"(v*[0-9]+[.])([0-9]+[.]*)+")


def url_contains_tarball_filename(
    urlparsed, extensions: List[str], raise_when_no_extension: bool = True
) -> bool:
    """Determine whether urlparsed contains a tarball filename ending with one of the
    extensions passed as parameter, path parts and query parameters are checked.

    This also account for the edge case of a filename with only a version as name (so no
    extension in the end.)

    Raises:
        ArtifactWithoutExtension in case no extension is available and
        raise_when_no_extension is True (the default)

    """
    paths = [Path(p) for (_, p) in [("_", urlparsed.path)] + parse_qsl(urlparsed.query)]
    match = any(
        path_part.endswith(tuple(extensions))
        for path in paths
        for path_part in path.parts
    )
    if match:
        return match
    if raise_when_no_extension and not any(path.suffix != "" for path in paths):
        raise ArtifactWithoutExtension
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
        return url_contains_tarball_filename(urlparsed, TARBALL_EXTENSIONS)

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
                    return _is_tarball(location), url
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
                        url_contains_tarball_filename(
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
