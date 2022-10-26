# Copyright (C) 2022 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from collections import defaultdict
import json
import logging
from pathlib import Path
from typing import Dict, List
from urllib.parse import urlparse

import pytest
import requests
from requests.exceptions import ConnectionError, InvalidSchema, SSLError

from swh.lister import TARBALL_EXTENSIONS
from swh.lister.nixguix.lister import (
    DEFAULT_EXTENSIONS_TO_IGNORE,
    POSSIBLE_TARBALL_MIMETYPES,
    ArtifactNatureMistyped,
    ArtifactNatureUndetected,
    ArtifactWithoutExtension,
    NixGuixLister,
    is_tarball,
    url_endswith,
)
from swh.lister.pattern import ListerStats

logger = logging.getLogger(__name__)

SOURCES = {
    "guix": {
        "repo": "https://git.savannah.gnu.org/cgit/guix.git/",
        "manifest": "https://guix.gnu.org/sources.json",
    },
    "nixpkgs": {
        "repo": "https://github.com/NixOS/nixpkgs",
        "manifest": "https://nix-community.github.io/nixpkgs-swh/sources-unstable.json",
    },
}


def page_response(datadir, instance: str = "success") -> List[Dict]:
    """Return list of repositories (out of test dataset)"""
    datapath = Path(datadir, f"sources-{instance}.json")
    return json.loads(datapath.read_text()) if datapath.exists else []


@pytest.mark.parametrize(
    "name,expected_result",
    [(f"one.{ext}", True) for ext in TARBALL_EXTENSIONS]
    + [(f"one.{ext}?foo=bar", True) for ext in TARBALL_EXTENSIONS]
    + [(f"one?p0=1&foo=bar.{ext}", True) for ext in DEFAULT_EXTENSIONS_TO_IGNORE]
    + [
        ("two?file=something.el", False),
        ("foo?two=two&three=three", False),
        ("v1.2.3", False),  # with raise_when_no_extension is False
        ("2048-game-20151026.1233", False),
        ("v2048-game-20151026.1233", False),
    ],
)
def test_url_endswith(name, expected_result):
    """It should detect whether url or query params of the urls ends with extensions"""
    urlparsed = urlparse(f"https://example.org/{name}")
    assert (
        url_endswith(
            urlparsed,
            TARBALL_EXTENSIONS + DEFAULT_EXTENSIONS_TO_IGNORE,
            raise_when_no_extension=False,
        )
        is expected_result
    )


@pytest.mark.parametrize(
    "name", ["foo?two=two&three=three", "tar.gz/0.1.5", "tar.gz/v10.3.1"]
)
def test_url_endswith_raise(name):
    """It should raise when the tested url has no extension"""
    urlparsed = urlparse(f"https://example.org/{name}")
    with pytest.raises(ArtifactWithoutExtension):
        url_endswith(urlparsed, ["unimportant"])


@pytest.mark.parametrize(
    "tarballs",
    [[f"one.{ext}", f"two.{ext}"] for ext in TARBALL_EXTENSIONS]
    + [[f"one.{ext}?foo=bar"] for ext in TARBALL_EXTENSIONS],
)
def test_is_tarball_simple(tarballs):
    """Simple check on tarball should  discriminate between tarball and file"""
    urls = [f"https://example.org/{tarball}" for tarball in tarballs]
    is_tar, origin = is_tarball(urls)
    assert is_tar is True
    assert origin == urls[0]


@pytest.mark.parametrize(
    "query_param",
    ["file", "f", "url", "name", "anykeyreally"],
)
def test_is_tarball_not_so_simple(query_param):
    """More involved check on tarball should discriminate between tarball and file"""
    url = f"https://example.org/download.php?foo=bar&{query_param}=one.tar.gz"
    is_tar, origin = is_tarball([url])
    assert is_tar is True
    assert origin == url


@pytest.mark.parametrize(
    "files",
    [
        ["abc.lisp"],
        ["one.abc", "two.bcd"],
        ["abc.c", "other.c"],
        ["one.scm?foo=bar", "two.scm?foo=bar"],
        ["config.nix", "flakes.nix"],
    ],
)
def test_is_tarball_simple_not_tarball(files):
    """Simple check on tarball should discriminate between tarball and file"""
    urls = [f"http://example.org/{file}" for file in files]
    is_tar, origin = is_tarball(urls)
    assert is_tar is False
    assert origin == urls[0]


def test_is_tarball_complex_with_no_result(requests_mock):
    """Complex tarball detection without proper information should fail."""
    # No extension, this won't detect immediately the nature of the url
    url = "https://example.org/crates/package/download"
    urls = [url]
    with pytest.raises(ArtifactNatureUndetected):
        is_tarball(urls)  # no request parameter, this cannot fallback, raises

    with pytest.raises(ArtifactNatureUndetected):
        requests_mock.head(
            url,
            status_code=404,  # not found so cannot detect anything
        )
        is_tarball(urls, requests)

    with pytest.raises(ArtifactNatureUndetected):
        requests_mock.head(
            url, headers={}
        )  # response ok without headers, cannot detect anything
        is_tarball(urls, requests)

    with pytest.raises(ArtifactNatureUndetected):
        fallback_url = "https://example.org/mirror/crates/package/download"
        requests_mock.head(
            url, headers={"location": fallback_url}  # still no extension, cannot detect
        )
        is_tarball(urls, requests)

    with pytest.raises(ArtifactNatureMistyped):
        is_tarball(["foo://example.org/unsupported-scheme"])

    with pytest.raises(ArtifactNatureMistyped):
        fallback_url = "foo://example.org/unsupported-scheme"
        requests_mock.head(
            url, headers={"location": fallback_url}  # still no extension, cannot detect
        )
        is_tarball(urls, requests)


@pytest.mark.parametrize(
    "fallback_url, expected_result",
    [
        ("https://example.org/mirror/crates/package/download.tar.gz", True),
        ("https://example.org/mirror/package/download.lisp", False),
    ],
)
def test_is_tarball_complex_with_location_result(
    requests_mock, fallback_url, expected_result
):
    """Complex tarball detection with information should detect artifact nature"""
    # No extension, this won't detect immediately the nature of the url
    url = "https://example.org/crates/package/download"
    urls = [url]

    # One scenario where the url renders a location with a proper extension
    requests_mock.head(url, headers={"location": fallback_url})
    is_tar, origin = is_tarball(urls, requests)
    assert is_tar == expected_result
    if is_tar:
        assert origin == fallback_url


@pytest.mark.parametrize(
    "content_type, expected_result",
    [("application/json", False), ("application/something", False)]
    + [(ext, True) for ext in POSSIBLE_TARBALL_MIMETYPES],
)
def test_is_tarball_complex_with_content_type_result(
    requests_mock, content_type, expected_result
):
    """Complex tarball detection with information should detect artifact nature"""
    # No extension, this won't detect immediately the nature of the url
    url = "https://example.org/crates/package/download"
    urls = [url]

    # One scenario where the url renders a location with a proper extension
    requests_mock.head(url, headers={"Content-Type": content_type})
    is_tar, origin = is_tarball(urls, requests)
    assert is_tar == expected_result
    if is_tar:
        assert origin == url


def test_lister_nixguix_ok(datadir, swh_scheduler, requests_mock):
    """NixGuixLister should list all origins per visit type"""
    url = SOURCES["guix"]["manifest"]
    origin_upstream = SOURCES["guix"]["repo"]
    lister = NixGuixLister(swh_scheduler, url=url, origin_upstream=origin_upstream)

    response = page_response(datadir, "success")
    requests_mock.get(
        url,
        [{"json": response}],
    )
    requests_mock.get(
        "https://api.github.com/repos/trie/trie",
        [{"json": {"html_url": "https://github.com/trie/trie.git"}}],
    )
    requests_mock.head(
        "http://git.marmaro.de/?p=mmh;a=snapshot;h=431604647f89d5aac7b199a7883e98e56e4ccf9e;sf=tgz",
        headers={"Content-Type": "application/gzip; charset=ISO-8859-1"},
    )
    requests_mock.head(
        "https://crates.io/api/v1/crates/syntect/4.6.0/download",
        headers={
            "Location": "https://static.crates.io/crates/syntect/syntect-4.6.0.crate"
        },
    )
    requests_mock.head(
        "https://codeload.github.com/fifengine/fifechan/tar.gz/0.1.5",
        headers={
            "Content-Type": "application/x-gzip",
        },
    )
    requests_mock.head(
        "https://codeload.github.com/unknown-horizons/unknown-horizons/tar.gz/2019.1",
        headers={
            "Content-Disposition": "attachment; filename=unknown-horizons-2019.1.tar.gz",
        },
    )
    requests_mock.head(
        "https://codeload.github.com/fifengine/fifengine/tar.gz/0.4.2",
        headers={
            "Content-Disposition": "attachment; name=fieldName; "
            "filename=fifengine-0.4.2.tar.gz; other=stuff",
        },
    )

    expected_visit_types = defaultdict(int)
    # origin upstream is added as origin
    expected_nb_origins = 1
    expected_visit_types["git"] += 1
    for artifact in response["sources"]:
        # Each artifact is considered an origin (even "url" artifacts with mirror urls)
        expected_nb_origins += 1
        artifact_type = artifact["type"]
        if artifact_type in [
            "git",
            "svn",
            "hg",
        ]:
            expected_visit_types[artifact_type] += 1
        elif artifact_type == "url":
            url = artifact["urls"][0]
            if url.endswith(".git"):
                expected_visit_types["git"] += 1
            elif url.endswith(".c") or url.endswith(".txt"):
                expected_visit_types["content"] += 1
            elif url.startswith("svn"):  # mistyped artifact rendered as vcs nonetheless
                expected_visit_types["svn"] += 1
            elif "crates.io" in url or "codeload.github.com" in url:
                expected_visit_types["directory"] += 1
            else:  # tarball artifacts
                expected_visit_types["directory"] += 1

    assert set(expected_visit_types.keys()) == {
        "content",
        "git",
        "svn",
        "hg",
        "directory",
    }

    listed_result = lister.run()

    # 1 page read is 1 origin
    nb_pages = expected_nb_origins
    assert listed_result == ListerStats(pages=nb_pages, origins=expected_nb_origins)

    scheduler_origins = lister.scheduler.get_listed_origins(
        lister.lister_obj.id
    ).results
    assert len(scheduler_origins) == expected_nb_origins

    mapping_visit_types = defaultdict(int)

    for listed_origin in scheduler_origins:
        assert listed_origin.visit_type in expected_visit_types
        # no last update is listed on those manifests
        assert listed_origin.last_update is None

        mapping_visit_types[listed_origin.visit_type] += 1

    assert dict(mapping_visit_types) == expected_visit_types


def test_lister_nixguix_mostly_noop(datadir, swh_scheduler, requests_mock):
    """NixGuixLister should ignore unsupported or incomplete or to ignore origins"""
    url = SOURCES["nixpkgs"]["manifest"]
    origin_upstream = SOURCES["nixpkgs"]["repo"]
    lister = NixGuixLister(
        swh_scheduler,
        url=url,
        origin_upstream=origin_upstream,
        extensions_to_ignore=["foobar"],
    )

    response = page_response(datadir, "failure")

    requests_mock.get(
        url,
        [{"json": response}],
    )
    # Amongst artifacts, this url does not allow to determine its nature (tarball, file)
    # It's ending up doing a http head query which ends up being 404, so it's skipped.
    requests_mock.head(
        "https://crates.io/api/v1/0.1.5/no-extension-and-head-404-so-skipped",
        status_code=404,
    )
    # Invalid schema for that origin (and no extension), so skip origin
    # from its name
    requests_mock.head(
        "ftp://ftp.ourproject.org/file-with-no-extension",
        exc=InvalidSchema,
    )
    # Cannot communicate with an expired cert, so skip origin
    requests_mock.head(
        "https://code.9front.org/hg/plan9front",
        exc=SSLError,
    )
    # Cannot connect to the site, so skip origin
    requests_mock.head(
        "https://git-tails.immerda.ch/onioncircuits",
        exc=ConnectionError,
    )

    listed_result = lister.run()
    # only the origin upstream is listed, every other entries are unsupported or incomplete
    assert listed_result == ListerStats(pages=1, origins=1)

    scheduler_origins = lister.scheduler.get_listed_origins(
        lister.lister_obj.id
    ).results
    assert len(scheduler_origins) == 1

    assert scheduler_origins[0].visit_type == "git"


def test_lister_nixguix_fail(datadir, swh_scheduler, requests_mock):
    url = SOURCES["nixpkgs"]["manifest"]
    origin_upstream = SOURCES["nixpkgs"]["repo"]
    lister = NixGuixLister(swh_scheduler, url=url, origin_upstream=origin_upstream)

    requests_mock.get(
        url,
        status_code=404,
    )

    with pytest.raises(requests.HTTPError):  # listing cannot continues so stop
        lister.run()

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    assert len(scheduler_origins) == 0
