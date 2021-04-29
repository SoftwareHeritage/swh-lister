# Copyright (C) 2021 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information
import functools
import json
from pathlib import Path
import re

import pytest
from requests.exceptions import HTTPError

from swh.lister import USER_AGENT
from swh.lister.sourceforge.lister import (
    MAIN_SITEMAP_URL,
    PROJECT_API_URL_FORMAT,
    SourceForgeLister,
)

# Mapping of project name to namespace
TEST_PROJECTS = {
    "adobexmp": "adobe",
    "backapps": "p",
    "backapps/website": "p",
    "mojunk": "p",
    "mramm": "p",
    "os3dmodels": "p",
}

URLS_MATCHER = {
    PROJECT_API_URL_FORMAT.format(namespace=namespace, project=project): project
    for project, namespace in TEST_PROJECTS.items()
}


def get_main_sitemap(datadir):
    return Path(datadir, "main-sitemap.xml").read_text()


def get_subsitemap_0(datadir):
    return Path(datadir, "subsitemap-0.xml").read_text()


def get_subsitemap_1(datadir):
    return Path(datadir, "subsitemap-1.xml").read_text()


def get_project_json(datadir, request, context):
    url = request.url
    project = URLS_MATCHER.get(url)
    assert project is not None, f"Url '{url}' could not be matched"
    project = project.replace("/", "-")
    return json.loads(Path(datadir, f"{project}.json").read_text())


def _check_request_headers(request):
    return request.headers.get("User-Agent") == USER_AGENT


def test_sourceforge_lister_full(swh_scheduler, requests_mock, datadir):
    """
    Simulate a full listing of an artificially restricted sourceforge.
    There are 5 different projects, spread over two sub-sitemaps, a few of which
    have multiple VCS listed, one has none, one is outside of the standard `/p/`
    namespace, some with custom mount points.
    All non-interesting but related entries have been kept.
    """
    lister = SourceForgeLister(scheduler=swh_scheduler)

    requests_mock.get(
        MAIN_SITEMAP_URL,
        text=get_main_sitemap(datadir),
        additional_matcher=_check_request_headers,
    )
    requests_mock.get(
        "https://sourceforge.net/allura_sitemap/sitemap-0.xml",
        text=get_subsitemap_0(datadir),
        additional_matcher=_check_request_headers,
    )
    requests_mock.get(
        "https://sourceforge.net/allura_sitemap/sitemap-1.xml",
        text=get_subsitemap_1(datadir),
        additional_matcher=_check_request_headers,
    )
    requests_mock.get(
        re.compile("https://sourceforge.net/rest/.*"),
        json=functools.partial(get_project_json, datadir),
        additional_matcher=_check_request_headers,
    )

    stats = lister.run()
    # - os3dmodels (2 repos),
    # - mramm (3 repos),
    # - mojunk (3 repos),
    # - backapps/website (1 repo).
    # adobe and backapps itself have no repos.
    assert stats.pages == 4
    assert stats.origins == 9

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    res = {o.url: (o.visit_type, str(o.last_update.date())) for o in scheduler_origins}
    assert res == {
        "svn.code.sf.net/p/backapps/website/code": ("svn", "2021-02-11"),
        "git.code.sf.net/p/os3dmodels/git": ("git", "2017-03-31"),
        "svn.code.sf.net/p/os3dmodels/svn": ("svn", "2017-03-31"),
        "git.code.sf.net/p/mramm/files": ("git", "2019-04-04"),
        "git.code.sf.net/p/mramm/git": ("git", "2019-04-04"),
        "svn.code.sf.net/p/mramm/svn": ("svn", "2019-04-04"),
        "git.code.sf.net/p/mojunk/git": ("git", "2017-12-31"),
        "git.code.sf.net/p/mojunk/git2": ("git", "2017-12-31"),
        "svn.code.sf.net/p/mojunk/svn": ("svn", "2017-12-31"),
    }


def test_sourceforge_lister_retry(swh_scheduler, requests_mock, mocker, datadir):
    # Exponential retries take a long time, so stub time.sleep
    mocked_sleep = mocker.patch("time.sleep", return_value=None)

    lister = SourceForgeLister(scheduler=swh_scheduler)

    requests_mock.get(
        MAIN_SITEMAP_URL,
        [
            {"status_code": 429},
            {"status_code": 429},
            {"text": get_main_sitemap(datadir)},
        ],
        additional_matcher=_check_request_headers,
    )
    requests_mock.get(
        "https://sourceforge.net/allura_sitemap/sitemap-0.xml",
        [{"status_code": 429}, {"text": get_subsitemap_0(datadir), "status_code": 301}],
        additional_matcher=_check_request_headers,
    )
    requests_mock.get(
        "https://sourceforge.net/allura_sitemap/sitemap-1.xml",
        [{"status_code": 429}, {"text": get_subsitemap_1(datadir)}],
        additional_matcher=_check_request_headers,
    )
    requests_mock.get(
        re.compile("https://sourceforge.net/rest/.*"),
        [{"status_code": 429}, {"json": functools.partial(get_project_json, datadir)}],
        additional_matcher=_check_request_headers,
    )

    stats = lister.run()
    # - os3dmodels (2 repos),
    # - mramm (3 repos),
    # - mojunk (3 repos),
    # - backapps/website (1 repo).
    # adobe and backapps itself have no repos.
    assert stats.pages == 4
    assert stats.origins == 9

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    assert {o.url: o.visit_type for o in scheduler_origins} == {
        "svn.code.sf.net/p/backapps/website/code": "svn",
        "git.code.sf.net/p/os3dmodels/git": "git",
        "svn.code.sf.net/p/os3dmodels/svn": "svn",
        "git.code.sf.net/p/mramm/files": "git",
        "git.code.sf.net/p/mramm/git": "git",
        "svn.code.sf.net/p/mramm/svn": "svn",
        "git.code.sf.net/p/mojunk/git": "git",
        "git.code.sf.net/p/mojunk/git2": "git",
        "svn.code.sf.net/p/mojunk/svn": "svn",
    }

    # Test `time.sleep` is called with exponential retries
    calls = [1.0, 10.0, 1.0, 1.0]
    mocked_sleep.assert_has_calls([mocker.call(c) for c in calls])


@pytest.mark.parametrize("status_code", [500, 503, 504, 403, 404])
def test_sourceforge_lister_http_error(swh_scheduler, requests_mock, status_code):
    lister = SourceForgeLister(scheduler=swh_scheduler)

    requests_mock.get(MAIN_SITEMAP_URL, status_code=status_code)

    with pytest.raises(HTTPError):
        lister.run()
