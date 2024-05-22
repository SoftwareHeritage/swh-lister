# Copyright (C) 2019-2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest

from swh.lister.cli import SUPPORTED_LISTERS, get_lister

lister_args = {
    "cgit": {
        "url": "https://git.eclipse.org/c/",
    },
    "phabricator": {
        "instance": "softwareheritage",
        "url": "https://forge.softwareheritage.org/api/diffusion.repository.search",
        "api_token": "bogus",
    },
    "gitea": {
        "instance": "try.gitea.io",
    },
    "tuleap": {
        "url": "https://tuleap.net",
    },
    "gitlab": {
        "instance": "gitlab.ow2.org",
    },
    "opam": {"url": "https://opam.ocaml.org", "instance": "opam"},
    "maven": {
        "url": "https://repo1.maven.org/maven2/",
        "index_url": "http://indexes/export.fld",
    },
    "gogs": {
        "instance": "try.gogs.io",
        "api_token": "secret",
    },
    "nixguix": {
        "url": "https://guix.gnu.org/sources.json",
        "origin_upstream": "https://git.savannah.gnu.org/cgit/guix.git/",
    },
    "rpm": {"url": "http://opensuse.org", "instance": "openSUSE", "rpm_src_data": []},
    "pagure": {"instance": "pagure.io"},
    "gitweb": {
        "url": "https://git.distorted.org.uk/~mdw/",
    },
    "gitiles": {
        "instance": "gerrit.googlesource.com",
    },
    "stagit": {
        "url": "https://git.codemadness.org",
    },
    "save-bulk": {
        "url": "https://example.org/origins/list/",
        "instance": "example.org",
    },
}


def test_get_lister_wrong_input():
    """Unsupported lister should raise"""
    with pytest.raises(ValueError) as e:
        get_lister("unknown", "db-url")

    assert "Invalid lister" in str(e.value)


def test_get_lister(swh_scheduler_config):
    """Instantiating a supported lister should be ok"""

    for lister_name in SUPPORTED_LISTERS:
        lst = get_lister(
            lister_name,
            scheduler={"cls": "local", **swh_scheduler_config},
            **lister_args.get(lister_name, {}),
        )
        assert hasattr(lst, "run")
