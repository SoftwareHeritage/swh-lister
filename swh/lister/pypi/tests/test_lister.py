# Copyright (C) 2019 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from pathlib import Path
from typing import List

import pytest
import requests

from swh.lister.pypi.lister import PyPILister
from swh.scheduler.model import ListedOrigin


@pytest.fixture
def pypi_packages_testdata(datadir):
    content = Path(datadir, "https_pypi.org", "simple").read_bytes()
    names = ["0lever-so", "0lever-utils", "0-orchestrator", "0wned"]
    urls = [PyPILister.PACKAGE_URL.format(package_name=n) for n in names]
    return content, names, urls


def check_listed_origins(lister_urls: List[str], scheduler_origins: List[ListedOrigin]):
    """Asserts that the two collections have the same origin URLs"""

    sorted_lister_urls = list(sorted(lister_urls))
    sorted_scheduler_origins = list(sorted(scheduler_origins))

    assert len(sorted_lister_urls) == len(sorted_scheduler_origins)

    for l_url, s_origin in zip(sorted_lister_urls, sorted_scheduler_origins):
        assert l_url == s_origin.url


def test_pypi_list(swh_scheduler, requests_mock, mocker, pypi_packages_testdata):

    t_content, t_names, t_urls = pypi_packages_testdata

    requests_mock.get(PyPILister.PACKAGE_LIST_URL, content=t_content)

    lister = PyPILister(scheduler=swh_scheduler)

    lister.get_origins_from_page = mocker.spy(lister, "get_origins_from_page")
    lister.session.get = mocker.spy(lister.session, "get")

    stats = lister.run()

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    lister.session.get.assert_called_once_with(lister.PACKAGE_LIST_URL)
    lister.get_origins_from_page.assert_called_once_with(t_names)

    assert stats.pages == 1
    assert stats.origins == 4
    assert len(scheduler_origins) == 4

    check_listed_origins(t_urls, scheduler_origins)

    assert lister.get_state_from_scheduler() is None


@pytest.mark.parametrize("http_code", [400, 429, 500])
def test_pypi_list_http_error(swh_scheduler, requests_mock, mocker, http_code):

    requests_mock.get(
        PyPILister.PACKAGE_LIST_URL, [{"content": None, "status_code": http_code},],
    )

    lister = PyPILister(scheduler=swh_scheduler)

    lister.session.get = mocker.spy(lister.session, "get")

    with pytest.raises(requests.HTTPError):
        lister.run()

    lister.session.get.assert_called_once_with(lister.PACKAGE_LIST_URL)

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    assert len(scheduler_origins) == 0


@pytest.mark.parametrize(
    "credentials, expected_credentials",
    [
        (None, []),
        ({"key": "value"}, []),
        (
            {"pypi": {"pypi": [{"username": "user", "password": "pass"}]}},
            [{"username": "user", "password": "pass"}],
        ),
    ],
)
def test_lister_pypi_instantiation_with_credentials(
    credentials, expected_credentials, swh_scheduler
):
    lister = PyPILister(swh_scheduler, credentials=credentials)

    # Credentials are allowed in constructor
    assert lister.credentials == expected_credentials


def test_lister_pypi_from_configfile(swh_scheduler_config, mocker):
    load_from_envvar = mocker.patch("swh.lister.pattern.load_from_envvar")
    load_from_envvar.return_value = {
        "scheduler": {"cls": "local", **swh_scheduler_config},
        "credentials": {},
    }
    lister = PyPILister.from_configfile()
    assert lister.scheduler is not None
    assert lister.credentials is not None
