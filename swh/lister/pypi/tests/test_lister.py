# Copyright (C) 2019-2021 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from collections import defaultdict
from datetime import datetime, timezone
from typing import List

import pytest

from swh.lister.pypi.lister import ChangelogEntry, PyPILister, pypi_url
from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin


def check_listed_origins(lister_urls: List[str], scheduler_origins: List[ListedOrigin]):
    """Asserts that the two collections have the same origin URLs"""
    assert set(lister_urls) == {origin.url for origin in scheduler_origins}


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


def to_serial(changelog_entry: ChangelogEntry) -> int:
    """Helper utility to read the serial entry in the tuple

    Args:
        changelog_entry: Changelog entry to read data from

    Returns:
        The serial from the entry

    """
    return changelog_entry[4]


def configure_scheduler_state(
    scheduler: SchedulerInterface, data: List[ChangelogEntry]
):
    """Allows to pre configure a last serial state for the lister consistent with the test
       data set (the last_serial will be something inferior than the most minimal serial
       in the data set).

    Args:
        scheduler: The actual scheduler instance used during test
        data: The actual dataset used during test

    """
    # Compute the lowest serial to make it a minimum state to store in the scheduler
    lowest_serial = min(map(to_serial, data))

    # We'll need to configure the scheduler's state
    lister_obj = scheduler.get_or_create_lister(
        name=PyPILister.LISTER_NAME, instance_name=PyPILister.INSTANCE
    )
    lister_obj.current_state = {"last_serial": lowest_serial - 10}
    scheduler.update_lister(lister_obj)


@pytest.fixture
def mock_pypi_xmlrpc(mocker, swh_scheduler):
    """This setups a lister so it can actually fake the call to the rpc service executed
       during an incremental listing.

    To retrieve or update the faked data, open a python3 toplevel and execute the
    following:

    .. code:: python

        from datetime import timezone, datetime, timedelta
        from xmlrpc.client import ServerProxy
        from swh.scheduler.utils import utcnow
        RPC_URL = "https://pypi.org/pypi"
        cli = ServerProxy(RPC_URL)
        last_serial = cli.changelog_last_serial()
        # 10854808
        last_state_serial = 2168587
        results = cli.changelog_since_serial(last_state_serial)

    Returns:
        the following Tuple[serial, List[PackageUpdate], MagicMock, MagicMock] type.

    """

    data = [
        ["wordsmith", None, 1465998124, "add Owner DoublePlusAwks", 2168628],
        ["wordsmith", "0.1", 1465998123, "new release", 2168629],
        ["wordsmith", "0.1", 1465998131, "update classifiers", 2168630],
        [
            "UFx",
            "1.0",
            1465998207,
            "update author_email, home_page, summary, description",
            2168631,
        ],
        ["UFx", "1.0", 1465998236, "remove file UFx-1.0.tar.gz", 2168632],
        ["wordsmith", "0.1", 1465998309, "update classifiers", 2168633],
        [
            "wordsmith",
            "0.1",
            1465998406,
            "update summary, description, classifiers",
            2168634,
        ],
        ["property-manager", "2.0", 1465998436, "new release", 2168635],
        [
            "property-manager",
            "2.0",
            1465998439,
            "add source file property-manager-2.0.tar.gz",
            2168636,
        ],
        ["numtest", "2.0.0", 1465998446, "new release", 2168637],
        ["property-manager", "2.1", 1465998468, "new release", 2168638],
        [
            "property-manager",
            "2.1",
            1465998472,
            "add source file property-manager-2.1.tar.gz",
            2168639,
        ],
        ["kafka-utils", "0.2.0", 1465998477, "new release", 2168640],
        [
            "kafka-utils",
            "0.2.0",
            1465998480,
            "add source file kafka-utils-0.2.0.tar.gz",
            2168641,
        ],
        ["numtest", "2.0.1", 1465998520, "new release", 2168642],
        ["coala-bears", "0.3.0.dev20160615134909", 1465998552, "new release", 2168643],
        [
            "coala-bears",
            "0.3.0.dev20160615134909",
            1465998556,
            "add py3 file coala_bears-0.3.0.dev20160615134909-py3-none-any.whl",
            2168644,
        ],
        ["django_sphinxsearch", "0.4.0", 1465998571, "new release", 2168645],
        [
            "django_sphinxsearch",
            "0.4.0",
            1465998573,
            "add source file django_sphinxsearch-0.4.0.tar.gz",
            2168646,
        ],
        [
            "coala-bears",
            "0.3.0.dev20160615134909",
            1465998589,
            "add source file coala-bears-0.3.0.dev20160615134909.tar.gz",
            2168647,
        ],
    ]
    highest_serial = min(map(to_serial, data))

    def sleep(seconds):
        pass

    mocker.patch("swh.lister.pypi.lister.sleep").return_value = sleep

    class FakeServerProxy:
        """Fake Server Proxy"""

        def changelog_last_serial(self):
            return highest_serial

        def changelog_since_serial(self, serial):
            return data

    mock_serverproxy = mocker.patch("swh.lister.pypi.lister.ServerProxy")
    mock_serverproxy.return_value = FakeServerProxy()

    return highest_serial, data, mock_serverproxy


@pytest.mark.parametrize("configure_state", [True, False])
def test_lister_pypi_run(mock_pypi_xmlrpc, swh_scheduler, configure_state):
    highest_serial, data, mock_serverproxy = mock_pypi_xmlrpc

    if configure_state:
        configure_scheduler_state(swh_scheduler, data)

    updated_packages = defaultdict(list)
    for [package, _, release_date, _, _] in data:
        updated_packages[package].append(release_date)

    assert len(updated_packages) > 0

    expected_last_updates = {
        pypi_url(package): datetime.fromtimestamp(max(releases)).replace(
            tzinfo=timezone.utc
        )
        for package, releases in updated_packages.items()
    }

    expected_pypi_urls = [pypi_url(package_name) for package_name in updated_packages]

    lister = PyPILister(scheduler=swh_scheduler)

    stats = lister.run()

    assert mock_serverproxy.called
    assert stats.pages == 1
    assert stats.origins == len(updated_packages)

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    assert len(scheduler_origins) == stats.origins

    check_listed_origins(expected_pypi_urls, scheduler_origins)

    actual_scheduler_state = lister.get_state_from_scheduler()
    # This new visit updated the state to the new one
    assert actual_scheduler_state.last_serial == highest_serial

    for listed_origin in scheduler_origins:
        assert listed_origin.last_update is not None
        assert listed_origin.last_update == expected_last_updates[listed_origin.url]


def test__if_rate_limited():
    # TODO
    pass
