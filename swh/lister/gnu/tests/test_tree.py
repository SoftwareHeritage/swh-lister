# Copyright (C) 2019 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json
from os import path

import pytest

from swh.lister.gnu.tree import (
    GNUTree,
    check_filename_is_archive,
    find_artifacts,
    format_date,
    get_version,
    load_raw_data,
)


def test_load_raw_data_from_query(requests_mock_datadir):
    actual_json = load_raw_data("https://ftp.gnu.org/tree.json.gz")
    assert actual_json is not None
    assert isinstance(actual_json, list)
    assert len(actual_json) == 2


def test_load_raw_data_from_query_failure(requests_mock_datadir):
    inexistant_url = "https://ftp2.gnu.org/tree.unknown.gz"
    with pytest.raises(ValueError, match="Error during query"):
        load_raw_data(inexistant_url)


def test_load_raw_data_from_file(datadir):
    filepath = path.join(datadir, "https_ftp.gnu.org", "tree.json.gz")
    actual_json = load_raw_data(filepath)
    assert actual_json is not None
    assert isinstance(actual_json, list)
    assert len(actual_json) == 2


def test_load_raw_data_from_file_failure(datadir):
    unknown_path = path.join(datadir, "ftp.gnu.org2", "tree.json.gz")
    with pytest.raises(FileNotFoundError):
        load_raw_data(unknown_path)


def test_tree_json(requests_mock_datadir):
    tree_json = GNUTree("https://ftp.gnu.org/tree.json.gz")

    assert tree_json.projects["https://ftp.gnu.org/gnu/8sync/"] == {
        "name": "8sync",
        "time_modified": "2017-03-18T06:10:08+00:00",
        "url": "https://ftp.gnu.org/gnu/8sync/",
    }

    assert tree_json.projects["https://ftp.gnu.org/gnu/3dldf/"] == {
        "name": "3dldf",
        "time_modified": "2013-12-13T19:00:36+00:00",
        "url": "https://ftp.gnu.org/gnu/3dldf/",
    }

    assert tree_json.projects["https://ftp.gnu.org/gnu/a2ps/"] == {
        "name": "a2ps",
        "time_modified": "2007-12-29T03:55:05+00:00",
        "url": "https://ftp.gnu.org/gnu/a2ps/",
    }

    assert tree_json.projects["https://ftp.gnu.org/old-gnu/xshogi/"] == {
        "name": "xshogi",
        "time_modified": "2003-08-02T11:15:22+00:00",
        "url": "https://ftp.gnu.org/old-gnu/xshogi/",
    }

    assert tree_json.artifacts["https://ftp.gnu.org/old-gnu/zlibc/"] == [
        {
            "url": "https://ftp.gnu.org/old-gnu/zlibc/zlibc-0.9b.tar.gz",  # noqa
            "length": 90106,
            "time": "1997-03-10T08:00:00+00:00",
            "filename": "zlibc-0.9b.tar.gz",
            "version": "0.9b",
        },
        {
            "url": "https://ftp.gnu.org/old-gnu/zlibc/zlibc-0.9e.tar.gz",  # noqa
            "length": 89625,
            "time": "1997-04-07T07:00:00+00:00",
            "filename": "zlibc-0.9e.tar.gz",
            "version": "0.9e",
        },
    ]


def test_tree_json_failures(requests_mock_datadir):
    url = "https://unknown/tree.json.gz"
    tree_json = GNUTree(url)

    with pytest.raises(ValueError, match="Error during query to %s" % url):
        tree_json.artifacts["https://ftp.gnu.org/gnu/3dldf/"]

    with pytest.raises(ValueError, match="Error during query to %s" % url):
        tree_json.projects["https://ftp.gnu.org/old-gnu/xshogi/"]


def test_find_artifacts_small_sample(datadir):
    expected_artifacts = [
        {
            "url": "/root/artanis/artanis-0.2.1.tar.bz2",
            "time": "2017-05-19T14:59:39+00:00",
            "length": 424081,
            "version": "0.2.1",
            "filename": "artanis-0.2.1.tar.bz2",
        },
        {
            "url": "/root/xboard/winboard/winboard-4_0_0-src.zip",  # noqa
            "time": "1998-06-21T09:55:00+00:00",
            "length": 1514448,
            "version": "4_0_0-src",
            "filename": "winboard-4_0_0-src.zip",
        },
        {
            "url": "/root/xboard/xboard-3.6.2.tar.gz",  # noqa
            "time": "1997-07-25T07:00:00+00:00",
            "length": 450164,
            "version": "3.6.2",
            "filename": "xboard-3.6.2.tar.gz",
        },
        {
            "url": "/root/xboard/xboard-4.0.0.tar.gz",  # noqa
            "time": "1998-06-21T09:55:00+00:00",
            "length": 514951,
            "version": "4.0.0",
            "filename": "xboard-4.0.0.tar.gz",
        },
    ]

    file_structure = json.load(open(path.join(datadir, "tree.min.json")))
    actual_artifacts = find_artifacts(file_structure, "/root/")
    assert actual_artifacts == expected_artifacts


def test_find_artifacts(datadir):
    file_structure = json.load(open(path.join(datadir, "tree.json")))
    actual_artifacts = find_artifacts(file_structure, "/root/")
    assert len(actual_artifacts) == 42 + 3  # tar + zip


def test_check_filename_is_archive():
    for ext in ["abc.xy.zip", "cvb.zip", "abc.tar.bz2", "something.tar"]:
        assert check_filename_is_archive(ext) is True

    for ext in ["abc.tar.gz.sig", "abc", "something.zip2", "foo.tar."]:
        assert check_filename_is_archive(ext) is False


def test_get_version():
    """Parsing version from url should yield some form of "sensible" version

    Given the dataset, it's not a simple task to extract correctly the version.

    """
    for url, expected_branchname in [
        ("https://gnu.org/sthg/info-2.1.0.tar.gz", "2.1.0"),
        ("https://gnu.org/sthg/info-2.1.2.zip", "2.1.2"),
        ("https://sthg.org/gnu/sthg.tar.gz", "sthg"),
        ("https://sthg.org/gnu/DLDF-1.1.4.tar.gz", "1.1.4"),
        ("https://sthg.org/gnu/anubis-latest.tar.bz2", "latest"),
        ("https://ftp.org/gnu/aris-w32.zip", "w32"),
        ("https://ftp.org/gnu/aris-w32-2.2.zip", "w32-2.2"),
        ("https://ftp.org/gnu/autogen.info.tar.gz", "autogen.info"),
        ("https://ftp.org/gnu/crypto-build-demo.tar.gz", "crypto-build-demo"),
        ("https://ftp.org/gnu/clue+clio+xit.clisp.tar.gz", "clue+clio+xit.clisp"),
        ("https://ftp.org/gnu/clue+clio.for-pcl.tar.gz", "clue+clio.for-pcl"),
        (
            "https://ftp.org/gnu/clisp-hppa2.0-hp-hpux10.20.tar.gz",
            "hppa2.0-hp-hpux10.20",
        ),
        ("clisp-i386-solaris2.6.tar.gz", "i386-solaris2.6"),
        ("clisp-mips-sgi-irix6.5.tar.gz", "mips-sgi-irix6.5"),
        ("clisp-powerpc-apple-macos.tar.gz", "powerpc-apple-macos"),
        ("clisp-powerpc-unknown-linuxlibc6.tar.gz", "powerpc-unknown-linuxlibc6"),
        ("clisp-rs6000-ibm-aix3.2.5.tar.gz", "rs6000-ibm-aix3.2.5"),
        ("clisp-sparc-redhat51-linux.tar.gz", "sparc-redhat51-linux"),
        ("clisp-sparc-sun-solaris2.4.tar.gz", "sparc-sun-solaris2.4"),
        ("clisp-sparc-sun-sunos4.1.3_U1.tar.gz", "sparc-sun-sunos4.1.3_U1"),
        ("clisp-2.25.1-powerpc-apple-MacOSX.tar.gz", "2.25.1-powerpc-apple-MacOSX"),
        (
            "clisp-2.27-PowerMacintosh-powerpc-Darwin-1.3.7.tar.gz",
            "2.27-PowerMacintosh-powerpc-Darwin-1.3.7",
        ),
        (
            "clisp-2.27-i686-unknown-Linux-2.2.19.tar.gz",
            "2.27-i686-unknown-Linux-2.2.19",
        ),
        (
            "clisp-2.28-i386-i386-freebsd-4.3-RELEASE.tar.gz",
            "2.28-i386-i386-freebsd-4.3-RELEASE",
        ),
        (
            "clisp-2.28-i686-unknown-cygwin_me-4.90-1.3.10.tar.gz",
            "2.28-i686-unknown-cygwin_me-4.90-1.3.10",
        ),
        (
            "clisp-2.29-i386-i386-freebsd-4.6-STABLE.tar.gz",
            "2.29-i386-i386-freebsd-4.6-STABLE",
        ),
        (
            "clisp-2.29-i686-unknown-cygwin_nt-5.0-1.3.12.tar.gz",
            "2.29-i686-unknown-cygwin_nt-5.0-1.3.12",
        ),
        (
            "gcl-2.5.3-ansi-japi-xdr.20030701_mingw32.zip",
            "2.5.3-ansi-japi-xdr.20030701_mingw32",
        ),
        ("gettext-runtime-0.13.1.bin.woe32.zip", "0.13.1.bin.woe32"),
        ("sather-logo_images.tar.gz", "sather-logo_images"),
        ("sather-specification-000328.html.tar.gz", "000328.html"),
        ("something-10.1.0.7z", "10.1.0"),
    ]:
        actual_branchname = get_version(url)

        assert actual_branchname == expected_branchname


def test_format_date():
    for timestamp, expected_isoformat_date in [
        (1489817408, "2017-03-18T06:10:08+00:00"),
        (1386961236, "2013-12-13T19:00:36+00:00"),
        ("1198900505", "2007-12-29T03:55:05+00:00"),
        (1059822922, "2003-08-02T11:15:22+00:00"),
        ("1489817408", "2017-03-18T06:10:08+00:00"),
    ]:
        actual_date = format_date(timestamp)
        assert actual_date == expected_isoformat_date

    with pytest.raises(ValueError):
        format_date("")
    with pytest.raises(TypeError):
        format_date(None)
