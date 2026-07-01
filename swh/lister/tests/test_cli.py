# Copyright (C) 2019-2026  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest

from swh.lister import get_lister, get_lister_names

lister_args = {
    "cgit": {
        "url": "https://git.eclipse.org/c/",
    },
    "forgejo": {
        "instance": "try.next.forgejo.org",
    },
    "gerrit": {"instance": "gerrit-review.googlesource.com"},
    "gitea": {
        "instance": "demo.gitea.com",
    },
    "gitiles": {
        "instance": "gerrit.googlesource.com",
    },
    "gitlab": {
        "instance": "gitlab.ow2.org",
    },
    "gitweb": {
        "url": "https://git.distorted.org.uk/~mdw/",
    },
    "gogs": {
        "instance": "try.gogs.io",
        "api_token": "secret",
    },
    "grokmirror": {"instance": "git.kernel.org"},
    "heptapod": {
        "instance": "foss.heptapod.net",
    },
    "hgweb": {"instance": "repo.mercurial-scm.org"},
    "maven": {
        "url": "https://repo1.maven.org/maven2/",
        "index_url": "http://indexes/export.fld",
    },
    "nixguix": {
        "url": "https://guix.gnu.org/sources.json",
        "origin_upstream": "https://git.savannah.gnu.org/cgit/guix.git/",
    },
    "opam": {"url": "https://opam.ocaml.org", "instance": "opam"},
    "pagure": {"instance": "pagure.io"},
    "phabricator": {
        "url": "https://forge.softwareheritage.org/",
        "instance": "softwareheritage",
        "api_token": "bogus",
    },
    "phorge": {
        "url": "https://we.phorge.it/",
        "instance": "wephorgeit",
        "api_token": "bogus",
    },
    "rpm": {"url": "http://opensuse.org", "instance": "openSUSE", "rpm_src_data": []},
    "save-bulk": {
        "url": "https://example.org/origins/list/",
        "instance": "example.org",
    },
    "stagit": {
        "url": "https://git.codemadness.org",
    },
    "tuleap": {
        "url": "https://tuleap.net",
    },
}


def test_get_lister_wrong_input():
    """Unsupported lister should raise"""
    with pytest.raises(ValueError) as e:
        get_lister("unknown", "db-url")

    assert "Invalid lister" in str(e.value)


def test_get_lister(swh_scheduler_config):
    """Instantiating a supported lister should be ok"""

    for lister_name in get_lister_names():
        lst = get_lister(
            lister_name,
            scheduler={"cls": "postgresql", **swh_scheduler_config},
            **lister_args.get(lister_name, {}),
        )
        assert hasattr(lst, "run")
