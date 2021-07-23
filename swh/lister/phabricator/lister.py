# Copyright (C) 2019-2021 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information
from collections import defaultdict
import logging
import random
from typing import Any, Dict, Iterator, List, Optional
from urllib.parse import urljoin

import requests

from swh.lister import USER_AGENT
from swh.lister.pattern import CredentialsType, StatelessLister
from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

logger = logging.getLogger(__name__)


PageType = List[Dict[str, Any]]


class PhabricatorLister(StatelessLister[PageType]):
    """
    List all repositories hosted on a Phabricator instance.

    Args:
        url: base URL of a phabricator forge
            (for instance https://forge.softwareheritage.org)
        instance: string identifier for the listed forge,
            URL network location will be used if not provided
        api_token: authentication token for Conduit API
    """

    LISTER_NAME = "phabricator"
    API_REPOSITORY_PATH = "/api/diffusion.repository.search"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: str,
        instance: Optional[str] = None,
        api_token: Optional[str] = None,
        credentials: CredentialsType = None,
    ):
        super().__init__(
            scheduler, urljoin(url, self.API_REPOSITORY_PATH), instance, credentials
        )

        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/json", "User-Agent": USER_AGENT}
        )

        if api_token is not None:
            self.api_token = api_token
        else:
            if not self.credentials:
                raise ValueError(
                    f"No credentials found for phabricator instance {self.instance};"
                    " Please set them in the lister configuration file."
                )

            self.api_token = random.choice(self.credentials)["password"]

    def get_request_params(self, after: Optional[str]) -> Dict[str, str]:
        """Get the query parameters for the request."""

        base_params = {
            # Stable order
            "order": "oldest",
            # Add all URIs to the response
            "attachments[uris]": "1",
            # API token from stored credentials
            "api.token": self.api_token,
        }

        if after is not None:
            base_params["after"] = after

        return base_params

    @staticmethod
    def filter_params(params: Dict[str, str]) -> Dict[str, str]:
        """Filter the parameters for debug purposes"""
        return {
            k: (v if k != "api.token" else "**redacted**") for k, v in params.items()
        }

    def get_pages(self) -> Iterator[PageType]:
        after: Optional[str] = None
        while True:
            params = self.get_request_params(after)
            logger.debug(
                "Retrieving results on URI %s with parameters %s",
                self.url,
                self.filter_params(params),
            )
            response = self.session.post(self.url, data=params)

            if response.status_code != 200:
                logger.warning(
                    "Unexpected HTTP status code %s on %s: %s",
                    response.status_code,
                    response.url,
                    response.content,
                )

            response.raise_for_status()

            response_data = response.json()

            if response_data.get("result") is None:
                logger.warning(
                    "Got unexpected response on %s: %s", response.url, response_data,
                )
                break

            result = response_data["result"]

            yield result["data"]
            after = None
            if "cursor" in result and "after" in result["cursor"]:
                after = result["cursor"]["after"]

            if not after:
                logger.debug("Empty `after` cursor. All done")
                break

    def get_origins_from_page(self, page: PageType) -> Iterator[ListedOrigin]:
        assert self.lister_obj.id is not None

        for repo in page:
            url = get_repo_url(repo["attachments"]["uris"]["uris"])
            if url is None:
                short_name: Optional[str] = None

                for field in "shortName", "name", "callsign":
                    short_name = repo["fields"].get(field)
                    if short_name:
                        break

                logger.warning(
                    "No valid url for repository [%s] (phid=%s)",
                    short_name or repo["phid"],
                    repo["phid"],
                )
                continue

            yield ListedOrigin(
                lister_id=self.lister_obj.id,
                url=url,
                visit_type=repo["fields"]["vcs"],
                # The "dateUpdated" field returned by the Phabricator API only refers to
                # the repository metadata; We can't use it for our purposes.
                last_update=None,
            )


def get_repo_url(attachments: List[Dict[str, Any]]) -> Optional[str]:
    """
    Return url for a hosted repository from its uris attachments according
    to the following priority lists:
    * protocol: https > http
    * identifier: shortname > callsign > id
    """
    processed_urls = defaultdict(dict)  # type: Dict[str, Any]
    for uri in attachments:
        protocol = uri["fields"]["builtin"]["protocol"]
        url = uri["fields"]["uri"]["effective"]
        identifier = uri["fields"]["builtin"]["identifier"]
        if protocol in ("http", "https"):
            processed_urls[protocol][identifier] = url
        elif protocol is None:
            for protocol in ("https", "http"):
                if url.startswith(protocol):
                    processed_urls[protocol]["undefined"] = url
                break
    for protocol in ["https", "http"]:
        for identifier in ["shortname", "callsign", "id", "undefined"]:
            if protocol in processed_urls and identifier in processed_urls[protocol]:
                return processed_urls[protocol][identifier]
    return None
