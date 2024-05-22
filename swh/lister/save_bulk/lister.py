# Copyright (C) 2024  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from dataclasses import asdict, dataclass, field
from http import HTTPStatus
import logging
import socket
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple, TypedDict
from urllib.parse import quote, urlparse

from breezy.builtins import cmd_info
from dulwich.porcelain import ls_remote
from mercurial import hg, ui
from requests import ConnectionError, RequestException
from subvertpy import SubversionException, client
from subvertpy.ra import Auth, get_username_provider

from swh.lister.utils import is_tarball
from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType, Lister

logger = logging.getLogger(__name__)


def _log_invalid_origin_type_for_url(
    origin_url: str, origin_type: str, err_msg: Optional[str] = None
):
    msg = f"Origin URL {origin_url} does not target a {origin_type}."
    if err_msg:
        msg += f"\nError details: {err_msg}"
    logger.info(msg)


def is_valid_tarball_url(origin_url: str) -> Tuple[bool, Optional[str]]:
    """Checks if an URL targets a tarball using a set of heuritiscs.

    Args:
        origin_url: The URL to check

    Returns:
        a tuple whose first member indicates if the URL targets a tarball and
            second member holds an optional error message if check failed
    """
    exc_str = None
    try:
        ret, _ = is_tarball([origin_url])
    except Exception as e:
        ret = False
        exc_str = str(e)
    if not ret:
        _log_invalid_origin_type_for_url(origin_url, "tarball", exc_str)
    return ret, exc_str


def is_valid_git_url(origin_url: str) -> Tuple[bool, Optional[str]]:
    """Check if an URL targets a public git repository by attempting to list
    its remote refs.

    Args:
        origin_url: The URL to check

    Returns:
        a tuple whose first member indicates if the URL targets a public git
            repository and second member holds an error message if check failed
    """
    try:
        ls_remote(origin_url)
    except Exception as e:
        exc_str = str(e)
        _log_invalid_origin_type_for_url(origin_url, "public git repository", exc_str)
        return False, exc_str
    else:
        return True, None


def is_valid_svn_url(origin_url: str) -> Tuple[bool, Optional[str]]:
    """Check if an URL targets a public subversion repository by attempting to get
    repository information.

    Args:
        origin_url: The URL to check

    Returns:
        a tuple whose first member indicates if the URL targets a public subversion
            repository and second member holds an error message if check failed
    """
    svn_client = client.Client(auth=Auth([get_username_provider()]))
    try:
        svn_client.info(quote(origin_url, safe="/:!$&'()*+,=@").rstrip("/"))
    except SubversionException as e:
        exc_str = str(e)
        _log_invalid_origin_type_for_url(
            origin_url, "public subversion repository", exc_str
        )
        return False, exc_str
    else:
        return True, None


def is_valid_hg_url(origin_url: str) -> Tuple[bool, Optional[str]]:
    """Check if an URL targets a public mercurial repository by attempting to connect
    to the remote repository.

    Args:
        origin_url: The URL to check

    Returns:
        a tuple whose first member indicates if the URL targets a public mercurial
            repository and second member holds an error message if check failed
    """
    hgui = ui.ui()
    hgui.setconfig(b"ui", b"interactive", False)
    try:
        hg.peer(hgui, {}, origin_url.encode())
    except Exception as e:
        exc_str = str(e)
        _log_invalid_origin_type_for_url(
            origin_url, "public mercurial repository", exc_str
        )
        return False, exc_str
    else:
        return True, None


def is_valid_bzr_url(origin_url: str) -> Tuple[bool, Optional[str]]:
    """Check if an URL targets a public bazaar repository by attempting to get
    repository information.

    Args:
        origin_url: The URL to check

    Returns:
        a tuple whose first member indicates if the URL targets a public bazaar
            repository and second member holds an error message if check failed
    """
    try:
        cmd_info().run_argv_aliases([origin_url])
    except Exception as e:
        exc_str = str(e)
        _log_invalid_origin_type_for_url(
            origin_url, "public bazaar repository", exc_str
        )
        return False, exc_str
    else:
        return True, None


def is_valid_cvs_url(origin_url: str) -> Tuple[bool, Optional[str]]:
    """Check if an URL matches one of the formats expected by the CVS loader of
    Software Heritage.

    Args:
        origin_url: The URL to check

    Returns:
        a tuple whose first member indicates if the URL matches one of the formats
            expected by the CVS loader and second member holds an error message if
            check failed.
    """
    err_msg = None
    rsync_url_format = "rsync://<hostname>[.*/]<project_name>/<module_name>"
    pserver_url_format = (
        "pserver://<usernmame>@<hostname>[.*/]<project_name>/<module_name>"
    )
    err_msg_prefix = (
        "The origin URL for the CVS repository is malformed, it should match"
    )

    parsed_url = urlparse(origin_url)
    ret = (
        parsed_url.scheme in ("rsync", "pserver")
        and len(parsed_url.path.strip("/").split("/")) >= 2
    )
    if parsed_url.scheme == "rsync":
        if not ret:
            err_msg = f"{err_msg_prefix} '{rsync_url_format}'"
    elif parsed_url.scheme == "pserver":
        ret = ret and parsed_url.username is not None
        if not ret:
            err_msg = f"{err_msg_prefix} '{pserver_url_format}'"
    else:
        err_msg = f"{err_msg_prefix} '{rsync_url_format}' or '{pserver_url_format}'"

    if not ret:
        _log_invalid_origin_type_for_url(origin_url, "CVS", err_msg)

    return ret, err_msg


CONNECTION_ERROR = "A connection error occurred when requesting origin URL."
HTTP_ERROR = "An HTTP error occurred when requesting origin URL"
HOSTNAME_ERROR = "The hostname could not be resolved."


VISIT_TYPE_ERROR: Dict[str, str] = {
    "tarball-directory": "The origin URL does not target a tarball.",
    "git": "The origin URL does not target a public git repository.",
    "svn": "The origin URL does not target a public subversion repository.",
    "hg": "The origin URL does not target a public mercurial repository.",
    "bzr": "The origin URL does not target a public bazaar repository.",
    "cvs": "The origin URL does not target a public CVS repository.",
}


class SubmittedOrigin(TypedDict):
    origin_url: str
    visit_type: str


@dataclass(frozen=True)
class RejectedOrigin:
    origin_url: str
    visit_type: str
    reason: str
    exception: Optional[str]


@dataclass
class SaveBulkListerState:
    """Stored lister state"""

    rejected_origins: List[RejectedOrigin] = field(default_factory=list)
    """
    List of origins rejected by the lister.
    """


SaveBulkListerPage = List[SubmittedOrigin]


class SaveBulkLister(Lister[SaveBulkListerState, SaveBulkListerPage]):
    """The save-bulk lister enables to verify a list of origins to archive provided
    by an HTTP endpoint. Its purpose is to avoid polluting the scheduler database with
    origins that cannot be loaded into the archive.

    Each origin is identified by an URL and a visit type. For a given visit type the
    lister is checking if the origin URL can be found and if the visit type is valid.

    The HTTP endpoint must return an origins list in a paginated way through the use
    of two integer query parameters: ``page`` indicates the page to fetch and `per_page`
    corresponds the number of origins in a page.
    The endpoint must return a JSON list in the following format:

    .. code-block:: JSON

        [
            {
                "origin_url": "https://git.example.org/user/project",
                "visit_type": "git"
            },
            {
                "origin_url": "https://example.org/downloads/project.tar.gz",
                "visit_type": "tarball-directory"
            }
        ]


    The supported visit types are those for VCS (``bzr``, ``cvs``, ``hg``, ``git``
    and ``svn``) plus the one for loading a tarball content into the archive
    (``tarball-directory``).

    Accepted origins are inserted or upserted in the scheduler database.

    Rejected origins are stored in the lister state.
    """

    LISTER_NAME = "save-bulk"

    def __init__(
        self,
        url: str,
        instance: str,
        scheduler: SchedulerInterface,
        credentials: Optional[CredentialsType] = None,
        max_origins_per_page: Optional[int] = None,
        max_pages: Optional[int] = None,
        enable_origins: bool = True,
        per_page: int = 1000,
    ):
        super().__init__(
            scheduler=scheduler,
            credentials=credentials,
            url=url,
            instance=instance,
            max_origins_per_page=max_origins_per_page,
            max_pages=max_pages,
            enable_origins=enable_origins,
        )
        self.rejected_origins: Set[RejectedOrigin] = set()
        self.per_page = per_page

    def state_from_dict(self, d: Dict[str, Any]) -> SaveBulkListerState:
        return SaveBulkListerState(
            rejected_origins=[
                RejectedOrigin(**rej) for rej in d.get("rejected_origins", [])
            ]
        )

    def state_to_dict(self, state: SaveBulkListerState) -> Dict[str, Any]:
        return {"rejected_origins": [asdict(rej) for rej in state.rejected_origins]}

    def get_pages(self) -> Iterator[SaveBulkListerPage]:
        current_page = 1
        origins = self.session.get(
            self.url, params={"page": current_page, "per_page": self.per_page}
        ).json()
        while origins:
            yield origins
            current_page += 1
            origins = self.session.get(
                self.url, params={"page": current_page, "per_page": self.per_page}
            ).json()

    def get_origins_from_page(
        self, origins: SaveBulkListerPage
    ) -> Iterator[ListedOrigin]:
        assert self.lister_obj.id is not None

        for origin in origins:
            origin_url = origin["origin_url"]
            visit_type = origin["visit_type"]

            logger.info(
                "Checking origin URL %s for visit type %s.", origin_url, visit_type
            )

            rejection_details = None
            rejection_exception = None

            parsed_url = urlparse(origin_url)
            if rejection_details is None:
                if parsed_url.scheme in ("http", "https"):
                    try:
                        response = self.session.head(origin_url, allow_redirects=True)
                        response.raise_for_status()
                    except ConnectionError as e:
                        logger.info(
                            "A connection error occurred when requesting %s.",
                            origin_url,
                        )
                        rejection_details = CONNECTION_ERROR
                        rejection_exception = str(e)
                    except RequestException as e:
                        if e.response is not None:
                            status = e.response.status_code
                            status_str = f"{status} - {HTTPStatus(status).phrase}"
                            logger.info(
                                "An HTTP error occurred when requesting %s: %s",
                                origin_url,
                                status_str,
                            )
                            rejection_details = f"{HTTP_ERROR}: {status_str}"
                        else:
                            logger.info(
                                "An HTTP error occurred when requesting %s.",
                                origin_url,
                            )
                            rejection_details = f"{HTTP_ERROR}."
                        rejection_exception = str(e)
                else:
                    try:
                        socket.getaddrinfo(parsed_url.netloc, port=None)
                    except OSError as e:
                        logger.info(
                            "Host name %s could not be resolved.", parsed_url.netloc
                        )
                        rejection_details = HOSTNAME_ERROR
                        rejection_exception = str(e)

            if rejection_details is None:
                visit_type_check_url = globals().get(
                    f"is_valid_{visit_type.split('-', 1)[0]}_url"
                )
                if visit_type_check_url:
                    url_valid, rejection_exception = visit_type_check_url(origin_url)
                    if not url_valid:
                        rejection_details = VISIT_TYPE_ERROR[visit_type]
                else:
                    rejection_details = (
                        f"Visit type {visit_type} is not supported "
                        "for bulk on-demand archival."
                    )
                    logger.info(
                        "Visit type %s for origin URL %s is not supported",
                        visit_type,
                        origin_url,
                    )

            if rejection_details is None:
                yield ListedOrigin(
                    lister_id=self.lister_obj.id,
                    url=origin["origin_url"],
                    visit_type=origin["visit_type"],
                    extra_loader_arguments=(
                        {"checksum_layout": "standard", "checksums": {}}
                        if origin["visit_type"] == "tarball-directory"
                        else {}
                    ),
                )
            else:
                self.rejected_origins.add(
                    RejectedOrigin(
                        origin_url=origin_url,
                        visit_type=visit_type,
                        reason=rejection_details,
                        exception=rejection_exception,
                    )
                )
                # update scheduler state at each rejected origin to get feedback
                # using Web API before end of listing
                self.state.rejected_origins = list(self.rejected_origins)
                self.set_state_in_scheduler()
