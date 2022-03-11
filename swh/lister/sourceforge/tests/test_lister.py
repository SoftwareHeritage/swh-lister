# Copyright (C) 2021 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information
import datetime
import functools
import json
from pathlib import Path
import re

from iso8601 import iso8601
import pytest
from requests.exceptions import HTTPError

from swh.lister import USER_AGENT
from swh.lister.sourceforge.lister import (
    MAIN_SITEMAP_URL,
    PROJECT_API_URL_FORMAT,
    SourceForgeLister,
    SourceForgeListerState,
)
from swh.lister.tests.test_utils import assert_sleep_calls
from swh.lister.utils import WAIT_EXP_BASE

# Mapping of project name to namespace
from swh.scheduler.model import ListedOrigin

TEST_PROJECTS = {
    "aaron": "p",
    "adobexmp": "adobe",
    "backapps": "p",
    "backapps/website": "p",
    "bzr-repo": "p",
    "mojunk": "p",
    "mramm": "p",
    "os3dmodels": "p",
    "random-mercurial": "p",
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


def get_cvs_info_page(datadir):
    return Path(datadir, "aaron.html").read_text()


def _check_request_headers(request):
    return request.headers.get("User-Agent") == USER_AGENT


def _check_listed_origins(lister, swh_scheduler):
    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    res = {o.url: (o.visit_type, str(o.last_update.date())) for o in scheduler_origins}
    assert res == {
        "https://svn.code.sf.net/p/backapps/website/code": ("svn", "2021-02-11"),
        "https://git.code.sf.net/p/os3dmodels/git": ("git", "2017-03-31"),
        "https://svn.code.sf.net/p/os3dmodels/svn": ("svn", "2017-03-31"),
        "https://git.code.sf.net/p/mramm/files": ("git", "2019-04-04"),
        "https://git.code.sf.net/p/mramm/git": ("git", "2019-04-04"),
        "https://svn.code.sf.net/p/mramm/svn": ("svn", "2019-04-04"),
        "https://git.code.sf.net/p/mojunk/git": ("git", "2017-12-31"),
        "https://git.code.sf.net/p/mojunk/git2": ("git", "2017-12-31"),
        "https://svn.code.sf.net/p/mojunk/svn": ("svn", "2017-12-31"),
        "http://hg.code.sf.net/p/random-mercurial/hg": ("hg", "2019-05-02"),
        "http://bzr-repo.bzr.sourceforge.net/bzrroot/bzr-repo": ("bzr", "2021-01-27"),
        "rsync://a.cvs.sourceforge.net/cvsroot/aaron/aaron": ("cvs", "2013-03-07"),
        "rsync://a.cvs.sourceforge.net/cvsroot/aaron/www": ("cvs", "2013-03-07"),
    }


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
    requests_mock.get(
        re.compile("http://aaron.cvs.sourceforge.net/"),
        text=get_cvs_info_page(datadir),
        additional_matcher=_check_request_headers,
    )

    stats = lister.run()
    # - os3dmodels (2 repos),
    # - mramm (3 repos),
    # - mojunk (3 repos),
    # - backapps/website (1 repo),
    # - random-mercurial (1 repo).
    # - bzr-repo (1 repo).
    # adobe and backapps itself have no repos.
    assert stats.pages == 7
    assert stats.origins == 13
    expected_state = {
        "subsitemap_last_modified": {
            "https://sourceforge.net/allura_sitemap/sitemap-0.xml": "2021-03-18",
            "https://sourceforge.net/allura_sitemap/sitemap-1.xml": "2021-03-18",
        },
        "empty_projects": {
            "https://sourceforge.net/rest/p/backapps": "2021-02-11",
            "https://sourceforge.net/rest/adobe/adobexmp": "2017-10-17",
        },
    }
    assert lister.state_to_dict(lister.state) == expected_state

    _check_listed_origins(lister, swh_scheduler)


def test_sourceforge_lister_incremental(swh_scheduler, requests_mock, datadir, mocker):
    """
    Simulate an incremental listing of an artificially restricted sourceforge.
    Same dataset as the full run, because it's enough to validate the different cases.
    """
    lister = SourceForgeLister(scheduler=swh_scheduler, incremental=True)

    requests_mock.get(
        MAIN_SITEMAP_URL,
        text=get_main_sitemap(datadir),
        additional_matcher=_check_request_headers,
    )

    def not_called(request, *args, **kwargs):
        raise AssertionError(f"Should not have been called: '{request.url}'")

    requests_mock.get(
        "https://sourceforge.net/allura_sitemap/sitemap-0.xml",
        text=get_subsitemap_0(datadir),
        additional_matcher=_check_request_headers,
    )
    requests_mock.get(
        "https://sourceforge.net/allura_sitemap/sitemap-1.xml",
        text=not_called,
        additional_matcher=_check_request_headers,
    )

    def filtered_get_project_json(request, context):
        # These projects should not be requested again
        assert URLS_MATCHER[request.url] not in {"adobe", "mojunk"}
        return get_project_json(datadir, request, context)

    requests_mock.get(
        re.compile("https://sourceforge.net/rest/.*"),
        json=filtered_get_project_json,
        additional_matcher=_check_request_headers,
    )

    requests_mock.get(
        re.compile("http://aaron.cvs.sourceforge.net/"),
        text=get_cvs_info_page(datadir),
        additional_matcher=_check_request_headers,
    )

    faked_listed_origins = [
        # mramm: changed
        ListedOrigin(
            lister_id=lister.lister_obj.id,
            visit_type="git",
            url="https://git.code.sf.net/p/mramm/files",
            last_update=iso8601.parse_date("2019-01-01"),
        ),
        ListedOrigin(
            lister_id=lister.lister_obj.id,
            visit_type="git",
            url="https://git.code.sf.net/p/mramm/git",
            last_update=iso8601.parse_date("2019-01-01"),
        ),
        ListedOrigin(
            lister_id=lister.lister_obj.id,
            visit_type="svn",
            url="https://svn.code.sf.net/p/mramm/svn",
            last_update=iso8601.parse_date("2019-01-01"),
        ),
        # stayed the same, even though its subsitemap has changed
        ListedOrigin(
            lister_id=lister.lister_obj.id,
            visit_type="git",
            url="https://git.code.sf.net/p/os3dmodels/git",
            last_update=iso8601.parse_date("2017-03-31"),
        ),
        ListedOrigin(
            lister_id=lister.lister_obj.id,
            visit_type="svn",
            url="https://svn.code.sf.net/p/os3dmodels/svn",
            last_update=iso8601.parse_date("2017-03-31"),
        ),
        # others: stayed the same, should be skipped
        ListedOrigin(
            lister_id=lister.lister_obj.id,
            visit_type="git",
            url="https://git.code.sf.net/p/mojunk/git",
            last_update=iso8601.parse_date("2017-12-31"),
        ),
        ListedOrigin(
            lister_id=lister.lister_obj.id,
            visit_type="git",
            url="https://git.code.sf.net/p/mojunk/git2",
            last_update=iso8601.parse_date("2017-12-31"),
        ),
        ListedOrigin(
            lister_id=lister.lister_obj.id,
            visit_type="svn",
            url="https://svn.code.sf.net/p/mojunk/svn",
            last_update=iso8601.parse_date("2017-12-31"),
        ),
        ListedOrigin(
            lister_id=lister.lister_obj.id,
            visit_type="svn",
            url="https://svn.code.sf.net/p/backapps/website/code",
            last_update=iso8601.parse_date("2021-02-11"),
        ),
        ListedOrigin(
            lister_id=lister.lister_obj.id,
            visit_type="hg",
            url="http://hg.code.sf.net/p/random-mercurial/hg",
            last_update=iso8601.parse_date("2019-05-02"),
        ),
        ListedOrigin(
            lister_id=lister.lister_obj.id,
            visit_type="bzr",
            url="http://bzr-repo.bzr.sourceforge.net/bzrroot/bzr-repo",
            last_update=iso8601.parse_date("2021-01-27"),
        ),
        ListedOrigin(
            lister_id=lister.lister_obj.id,
            visit_type="cvs",
            url="rsync://a.cvs.sourceforge.net/cvsroot/aaron/aaron",
            last_update=iso8601.parse_date("2013-03-07"),
        ),
        ListedOrigin(
            lister_id=lister.lister_obj.id,
            visit_type="cvs",
            url="rsync://a.cvs.sourceforge.net/cvsroot/aaron/www",
            last_update=iso8601.parse_date("2013-03-07"),
        ),
    ]
    swh_scheduler.record_listed_origins(faked_listed_origins)

    to_date = datetime.date.fromisoformat
    faked_state = SourceForgeListerState(
        subsitemap_last_modified={
            # changed
            "https://sourceforge.net/allura_sitemap/sitemap-0.xml": to_date(
                "2021-02-18"
            ),
            # stayed the same
            "https://sourceforge.net/allura_sitemap/sitemap-1.xml": to_date(
                "2021-03-18"
            ),
        },
        empty_projects={
            "https://sourceforge.net/rest/p/backapps": to_date("2020-02-11"),
            "https://sourceforge.net/rest/adobe/adobexmp": to_date("2017-10-17"),
        },
    )
    lister.state = faked_state

    stats = lister.run()

    # - mramm (3 repos),  # changed
    assert stats.pages == 1
    assert stats.origins == 3
    expected_state = {
        "subsitemap_last_modified": {
            "https://sourceforge.net/allura_sitemap/sitemap-0.xml": "2021-03-18",
            "https://sourceforge.net/allura_sitemap/sitemap-1.xml": "2021-03-18",
        },
        "empty_projects": {
            "https://sourceforge.net/rest/p/backapps": "2021-02-11",  # changed
            "https://sourceforge.net/rest/adobe/adobexmp": "2017-10-17",
        },
    }
    assert lister.state_to_dict(lister.state) == expected_state

    # origins have been updated
    _check_listed_origins(lister, swh_scheduler)


def test_sourceforge_lister_retry(swh_scheduler, requests_mock, mocker, datadir):

    lister = SourceForgeLister(scheduler=swh_scheduler)

    # Exponential retries take a long time, so stub time.sleep
    mocked_sleep = mocker.patch.object(lister.page_request.retry, "sleep")

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

    requests_mock.get(
        re.compile("http://aaron.cvs.sourceforge.net/"),
        text=get_cvs_info_page(datadir),
        additional_matcher=_check_request_headers,
    )

    stats = lister.run()
    # - os3dmodels (2 repos),
    # - mramm (3 repos),
    # - mojunk (3 repos),
    # - backapps/website (1 repo),
    # - random-mercurial (1 repo).
    # - bzr-repo (1 repo).
    # adobe and backapps itself have no repos.
    assert stats.pages == 7
    assert stats.origins == 13

    _check_listed_origins(lister, swh_scheduler)

    # Test `time.sleep` is called with exponential retries
    assert_sleep_calls(mocker, mocked_sleep, [1, WAIT_EXP_BASE, 1, 1])


@pytest.mark.parametrize("status_code", [500, 503, 504, 403, 404])
def test_sourceforge_lister_http_error(
    swh_scheduler, requests_mock, status_code, mocker
):
    lister = SourceForgeLister(scheduler=swh_scheduler)

    # Exponential retries take a long time, so stub time.sleep
    mocked_sleep = mocker.patch.object(lister.page_request.retry, "sleep")

    requests_mock.get(MAIN_SITEMAP_URL, status_code=status_code)

    with pytest.raises(HTTPError):
        lister.run()

    exp_retries = []
    if status_code >= 500:
        exp_retries = [1.0, 10.0, 100.0, 1000.0]

    assert_sleep_calls(mocker, mocked_sleep, exp_retries)


@pytest.mark.parametrize("status_code", [500, 503, 504, 403, 404])
def test_sourceforge_lister_project_error(
    datadir, swh_scheduler, requests_mock, status_code, mocker
):
    lister = SourceForgeLister(scheduler=swh_scheduler)
    # Exponential retries take a long time, so stub time.sleep
    mocker.patch.object(lister.page_request.retry, "sleep")

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
    # Request mocks precedence is LIFO
    requests_mock.get(
        re.compile("https://sourceforge.net/rest/.*"),
        json=functools.partial(get_project_json, datadir),
        additional_matcher=_check_request_headers,
    )
    # Make all `mramm` requests fail
    # `mramm` is in subsitemap 0, which ensures we keep listing after an error.
    requests_mock.get(
        re.compile("https://sourceforge.net/rest/p/mramm"), status_code=status_code
    )

    # Make request to CVS info page fail
    requests_mock.get(
        re.compile("http://aaron.cvs.sourceforge.net/"), status_code=status_code
    )

    stats = lister.run()
    # - os3dmodels (2 repos),
    # - mojunk (3 repos),
    # - backapps/website (1 repo),
    # - random-mercurial (1 repo).
    # - bzr-repo (1 repo).
    # adobe and backapps itself have no repos.
    # Did *not* list mramm
    assert stats.pages == 5
    assert stats.origins == 8

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    res = {o.url: (o.visit_type, str(o.last_update.date())) for o in scheduler_origins}
    # Ensure no `mramm` origins are listed, but all others are.
    assert res == {
        "https://svn.code.sf.net/p/backapps/website/code": ("svn", "2021-02-11"),
        "https://git.code.sf.net/p/os3dmodels/git": ("git", "2017-03-31"),
        "https://svn.code.sf.net/p/os3dmodels/svn": ("svn", "2017-03-31"),
        "https://git.code.sf.net/p/mojunk/git": ("git", "2017-12-31"),
        "https://git.code.sf.net/p/mojunk/git2": ("git", "2017-12-31"),
        "https://svn.code.sf.net/p/mojunk/svn": ("svn", "2017-12-31"),
        "http://hg.code.sf.net/p/random-mercurial/hg": ("hg", "2019-05-02"),
        "http://bzr-repo.bzr.sourceforge.net/bzrroot/bzr-repo": ("bzr", "2021-01-27"),
    }
