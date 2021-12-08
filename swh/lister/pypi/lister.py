# Copyright (C) 2018-2021 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import logging
from time import sleep
from typing import Any, Dict, Iterator, List, Optional, Tuple
from xmlrpc.client import Fault, ServerProxy

from tenacity.before_sleep import before_sleep_log

from swh.lister.utils import throttling_retry
from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, Lister

logger = logging.getLogger(__name__)

# Type returned by the XML-RPC changelog call:
# package, version, release timestamp, description, serial
ChangelogEntry = Tuple[str, str, int, str, int]
# Manipulated package updated type which is a subset information
# of the ChangelogEntry type: package, max release date
PackageUpdate = Tuple[str, datetime]
# Type returned by listing a page of results
PackageListPage = List[PackageUpdate]


@dataclass
class PyPIListerState:
    """State of PyPI lister"""

    last_serial: Optional[int] = None
    """Last seen serial when visiting the pypi instance"""


def _if_rate_limited(retry_state) -> bool:
    """Custom tenacity retry predicate to handle xmlrpc client error:

    .. code::

        xmlrpc.client.Fault: <Fault -32500: 'HTTPTooManyRequests: The action could not
        be performed because there were too many requests by the client. Limit may reset
        in 1 seconds.'>

    """
    attempt = retry_state.outcome
    return attempt.failed and isinstance(attempt.exception(), Fault)


def pypi_url(package_name: str) -> str:
    """Build pypi url out of a package name.

    """
    return PyPILister.PACKAGE_URL.format(package_name=package_name)


class PyPILister(Lister[PyPIListerState, PackageListPage]):
    """List origins from PyPI.

    """

    LISTER_NAME = "pypi"
    INSTANCE = "pypi"  # As of today only the main pypi.org is used
    PACKAGE_LIST_URL = "https://pypi.org/pypi"  # XML-RPC url
    PACKAGE_URL = "https://pypi.org/project/{package_name}/"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        credentials: Optional[CredentialsType] = None,
    ):
        super().__init__(
            scheduler=scheduler,
            url=self.PACKAGE_LIST_URL,
            instance=self.INSTANCE,
            credentials=credentials,
        )

        # used as termination condition and if useful, becomes the new state when the
        # visit is done
        self.last_processed_serial: Optional[int] = None

    def state_from_dict(self, d: Dict[str, Any]) -> PyPIListerState:
        return PyPIListerState(last_serial=d.get("last_serial"))

    def state_to_dict(self, state: PyPIListerState) -> Dict[str, Any]:
        return asdict(state)

    @throttling_retry(
        retry=_if_rate_limited, before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def _changelog_last_serial(self, client: ServerProxy) -> int:
        """Internal detail to allow throttling when calling the changelog last entry"""
        serial = client.changelog_last_serial()
        assert isinstance(serial, int)
        return serial

    @throttling_retry(
        retry=_if_rate_limited, before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def _changelog_since_serial(
        self, client: ServerProxy, serial: int
    ) -> List[ChangelogEntry]:
        """Internal detail to allow throttling when calling the changelog listing"""
        sleep(1)  # to avoid the initial warning about throttling
        return client.changelog_since_serial(serial)  # type: ignore

    def get_pages(self) -> Iterator[PackageListPage]:
        """Iterate other changelog events per package, determine the max release date for that
           package and use that max release date as last_update. When the execution is
           done, this will also set the self.last_processed_serial attribute so we can
           finalize the state of the lister for the next visit.

        Yields:
            List of Tuple of (package-name, max release-date)

        """
        client = ServerProxy(self.url)

        last_processed_serial = -1
        if self.state.last_serial is not None:
            last_processed_serial = self.state.last_serial
        upstream_last_serial = self._changelog_last_serial(client)

        # Paginate through result of pypi, until we read everything
        while last_processed_serial < upstream_last_serial:
            updated_packages = defaultdict(list)

            for package, _, release_date, _, serial in self._changelog_since_serial(
                client, last_processed_serial
            ):
                updated_packages[package].append(release_date)
                # Compute the max serial so we can stop when done
                last_processed_serial = max(last_processed_serial, serial)

            # Returns pages of result to flush regularly
            yield [
                (
                    pypi_url(package),
                    datetime.fromtimestamp(max(release_dates)).replace(
                        tzinfo=timezone.utc
                    ),
                )
                for package, release_dates in updated_packages.items()
            ]

        self.last_processed_serial = upstream_last_serial

    def get_origins_from_page(
        self, packages: PackageListPage
    ) -> Iterator[ListedOrigin]:
        """Convert a page of PyPI repositories into a list of ListedOrigins."""
        assert self.lister_obj.id is not None

        for origin, last_update in packages:
            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                url=origin,
                visit_type="pypi",
                last_update=last_update,
            )

    def finalize(self):
        """Finalize the visit state by updating with the new last_serial if updates
           actually happened.

        """
        self.updated = (
            self.state
            and self.state.last_serial
            and self.last_processed_serial
            and self.state.last_serial < self.last_processed_serial
        ) or (not self.state.last_serial and self.last_processed_serial)
        if self.updated:
            self.state.last_serial = self.last_processed_serial
