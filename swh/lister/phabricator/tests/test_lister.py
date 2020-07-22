# Copyright (C) 2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import importlib.resources
import json

from swh.lister.phabricator.lister import get_repo_url


def test_get_repo_url():
    with importlib.resources.open_text(
        "swh.lister.phabricator.tests.data", "api_first_response.json"
    ) as f:
        api_response = json.load(f)
    repos = api_response["result"]["data"]
    for repo in repos:
        expected_name = "https://forge.softwareheritage.org/source/%s.git" % (
            repo["fields"]["shortName"]
        )
        assert get_repo_url(repo["attachments"]["uris"]["uris"]) == expected_name

    with importlib.resources.open_text(
        "swh.lister.phabricator.tests.data", "api_response_undefined_protocol.json",
    ) as f:
        repo = json.load(f)
    expected_name = "https://svn.blender.org/svnroot/bf-blender/"
    assert get_repo_url(repo["attachments"]["uris"]["uris"]) == expected_name
