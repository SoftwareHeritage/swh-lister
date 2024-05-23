# Copyright (C) 2022-2024 The Software Heritage developers
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
    VCS_ARTIFACT_TYPE_TO_VISIT_TYPE,
    NixGuixLister,
    is_tarball,
    url_contains_tarball_filename,
)
from swh.lister.pattern import ListerStats
from swh.lister.utils import (
    ArtifactNatureMistyped,
    ArtifactNatureUndetected,
    ArtifactWithoutExtension,
)

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
    return json.loads(datapath.read_text()) if datapath.exists() else []


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
        url_contains_tarball_filename(
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
        url_contains_tarball_filename(urlparsed, ["unimportant"])


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
    "url",
    [
        "https://example.org/download/one.tar.gz/other/path/parts",
        "https://example.org/download.php?foo=bar&file=one.tar.gz",
    ],
)
def test_is_tarball_not_so_simple(url):
    """Detect tarball URL when filename is not in the last path parts or
    in a query parameter"""
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
        assert origin == url


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
    requests_mock.get(
        "https://api.github.com/repos/supercollider/supercollider",
        [{"json": {"html_url": "https://github.com/supercollider/supercollider"}}],
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
    # The url will not succeed, so the other url will be fetched
    requests_mock.head(
        "ftp://ftp.ourproject.org/pub/ytalk",
        status_code=404,
    )

    expected_visit_types = defaultdict(int)
    # origin upstream is added as origin
    expected_nb_pages = 1

    expected_visit_types["git"] += 1
    for artifact in response["sources"]:
        expected_nb_pages += 1
        artifact_type = artifact["type"]
        if artifact_type in [
            "git",
            "svn",
            "hg",
        ]:
            expected_visit_types[artifact_type] += 1
            outputHashMode = artifact.get("outputHashMode", "flat")
            if outputHashMode == "recursive":
                # Those are specific
                visit_type = VCS_ARTIFACT_TYPE_TO_VISIT_TYPE[artifact_type]
                expected_visit_types[visit_type] += 1
                # 1 origin of type `visit_type` is listed in that case too
                expected_nb_pages += 1

        elif artifact_type == "url":
            url = artifact["urls"][0]
            if url.endswith(".git"):
                visit_type = "git"
            elif url.endswith(".c") or url.endswith(".txt"):
                visit_type = "content"
            elif url.startswith("svn"):  # mistyped artifact rendered as vcs nonetheless
                visit_type = "svn"
            elif "crates.io" in url or "codeload.github.com" in url:
                visit_type = "tarball-directory"
            else:  # tarball artifacts
                visit_type = "tarball-directory"
            expected_visit_types[visit_type] += 1

    assert set(expected_visit_types.keys()) == {
        "content",
        "git",
        "svn",
        "hg",
        "tarball-directory",
        "git-checkout",
        "svn-export",
        "hg-checkout",
    }

    listed_result = lister.run()

    # Each artifact is considered an origin (even "url" artifacts with mirror urls) but
    expected_nb_origins = sum(expected_visit_types.values())
    # 3 origins have their recursive hash mentioned, they are sent both as vcs and as
    # specific vcs directory to ingest. So they are duplicated with visit_type 'git' and
    # 'git-checkout', 'svn' and 'svn-export', 'hg' and 'hg-checkout'.
    expected_nb_dictincts_origins = expected_nb_origins - 4

    # 1 page read is 1 origin
    assert listed_result == ListerStats(
        pages=expected_nb_pages, origins=expected_nb_dictincts_origins
    )

    scheduler_origins = lister.scheduler.get_listed_origins(
        lister.lister_obj.id
    ).results
    assert len(scheduler_origins) == expected_nb_origins

    # The test dataset will trigger some origins duplicated as mentioned above
    # Let's check them out
    duplicated_visit_types = []
    for duplicated_url in [
        "https://example.org/rgerganov/footswitch",
        "https://hg.sr.ht/~olly/yoyo",
        "svn://svn.savannah.gnu.org/apl/trunk",
        "https://github.com/supercollider/supercollider",
    ]:
        duplicated_visit_types.extend(
            [
                origin.visit_type
                for origin in scheduler_origins
                if origin.url == duplicated_url
            ]
        )

    assert len(duplicated_visit_types) == 8
    assert set(duplicated_visit_types) == {
        "git",
        "git-checkout",
        "svn",
        "svn-export",
        "hg",
        "hg-checkout",
    }

    mapping_visit_types = defaultdict(int)

    for listed_origin in scheduler_origins:
        assert listed_origin.visit_type in expected_visit_types
        # no last update is listed on those manifests
        assert listed_origin.last_update is None

        if listed_origin.visit_type in {"git-checkout", "svn-export", "hg-checkout"}:
            assert listed_origin.extra_loader_arguments["ref"] is not None
            if listed_origin.url == "https://github.com/supercollider/supercollider":
                assert listed_origin.extra_loader_arguments["submodules"] is True
            else:
                assert "submodules" not in listed_origin.extra_loader_arguments

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
    # Either not found or invalid schema for that origin (and no extension), so skip
    # origin from its name
    requests_mock.head(
        "ftp://example.mirror.org/extensionless-file",
        status_code=404,
    )
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

    expected_origins = ["https://github.com/NixOS/nixpkgs"]
    scheduler_origins = lister.scheduler.get_listed_origins(
        lister.lister_obj.id
    ).results
    scheduler_origin_urls = [orig.url for orig in scheduler_origins]

    assert scheduler_origin_urls == expected_origins

    # only the origin upstream is listed, every other entries are unsupported or incomplete
    assert listed_result == ListerStats(pages=1, origins=1), (
        f"Expected origins: {' '.join(expected_origins)}, got: "
        f"{' '.join(scheduler_origin_urls)}"
    )

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


def test_lister_nixguix_svn_export_sub_trees(datadir, swh_scheduler, requests_mock):
    """NixGuixLister should handle svn-export visit types exporting a subset of
    a subversion source tree (e.g. Tex Live packages for Guix)"""
    url = SOURCES["guix"]["manifest"]
    origin_upstream = SOURCES["guix"]["repo"]
    lister = NixGuixLister(swh_scheduler, url=url, origin_upstream=origin_upstream)

    response = page_response(datadir, "texlive")
    requests_mock.get(url, [{"json": response}])

    listed_result = lister.run()

    assert listed_result == ListerStats(pages=7, origins=5)

    scheduler_origins = {
        origin.url: origin
        for origin in lister.scheduler.get_listed_origins(lister.lister_obj.id).results
    }

    for source in response["sources"]:
        svn_url = source["svn_url"]
        origin_url = f"{source['svn_url']}?nar={source['integrity']}"
        assert origin_url in scheduler_origins
        assert "svn_url" in scheduler_origins[origin_url].extra_loader_arguments
        assert (
            scheduler_origins[origin_url].extra_loader_arguments["svn_url"] == svn_url
        )
        assert "svn_paths" in scheduler_origins[origin_url].extra_loader_arguments
        assert (
            scheduler_origins[origin_url].extra_loader_arguments["svn_paths"]
            == source["svn_files"]
        )
