# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from collections import defaultdict
import logging
import random
from typing import Any, Dict, List, Optional
import urllib.parse

from requests import Response
from sqlalchemy import func

from swh.lister.core.indexing_lister import IndexingHttpLister
from swh.lister.phabricator.models import PhabricatorModel

logger = logging.getLogger(__name__)


class PhabricatorLister(IndexingHttpLister):
    PATH_TEMPLATE = "?order=oldest&attachments[uris]=1&after=%s"
    DEFAULT_URL = "https://forge.softwareheritage.org/api/diffusion.repository.search"
    MODEL = PhabricatorModel
    LISTER_NAME = "phabricator"

    def __init__(self, url=None, instance=None, override_config=None):
        super().__init__(url=url, override_config=override_config)
        if not instance:
            instance = urllib.parse.urlparse(self.url).hostname
        self.instance = instance

    def request_params(self, identifier: str) -> Dict[str, Any]:
        """Override the default params behavior to retrieve the api token

        Credentials are stored as:

        credentials:
          phabricator:
            <instance>:
              - username: <account>
                password: <api-token>

        """
        creds = self.request_instance_credentials()
        if not creds:
            raise ValueError(
                "Phabricator forge needs authentication credential to list."
            )
        api_token = random.choice(creds)["password"]

        return {
            "headers": self.request_headers() or {},
            "params": {"api.token": api_token},
        }

    def request_headers(self):
        """
        (Override) Set requests headers to send when querying the
        Phabricator API
        """
        headers = super().request_headers()
        headers["Accept"] = "application/json"
        return headers

    def get_model_from_repo(self, repo: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        url = get_repo_url(repo["attachments"]["uris"]["uris"])
        if url is None:
            return None
        return {
            "uid": url,
            "indexable": repo["id"],
            "name": repo["fields"]["shortName"],
            "full_name": repo["fields"]["name"],
            "html_url": url,
            "origin_url": url,
            "origin_type": repo["fields"]["vcs"],
            "instance": self.instance,
        }

    def get_next_target_from_response(self, response: Response) -> Optional[int]:
        body = response.json()["result"]["cursor"]
        if body["after"] and body["after"] != "null":
            return int(body["after"])
        return None

    def transport_response_simplified(
        self, response: Response
    ) -> List[Optional[Dict[str, Any]]]:
        repos = response.json()
        if repos["result"] is None:
            raise ValueError(
                "Problem during information fetch: %s" % repos["error_code"]
            )
        repos = repos["result"]["data"]
        return [self.get_model_from_repo(repo) for repo in repos]

    def filter_before_inject(self, models_list):
        """
        (Overrides) IndexingLister.filter_before_inject
        Bounds query results by this Lister's set max_index.
        """
        models_list = [m for m in models_list if m is not None]
        return super().filter_before_inject(models_list)

    def disable_deleted_repo_tasks(self, index: int, next_index: int, keep_these: str):
        """
        (Overrides) Fix provided index value to avoid:

            - database query error
            - erroneously disabling some scheduler tasks
        """
        # First call to the Phabricator API uses an empty 'after' parameter,
        # so set the index to 0 to avoid database query error
        if index == "":
            index = 0
        # Next listed repository ids are strictly greater than the 'after'
        # parameter, so increment the index to avoid disabling the latest
        # created task when processing a new repositories page returned by
        # the Phabricator API
        else:
            index = index + 1
        return super().disable_deleted_repo_tasks(index, next_index, keep_these)

    def db_first_index(self) -> Optional[int]:
        """
        (Overrides) Filter results by Phabricator instance

        Returns:
            the smallest indexable value of all repos in the db
        """
        t = self.db_session.query(func.min(self.MODEL.indexable))
        t = t.filter(self.MODEL.instance == self.instance).first()
        if t:
            return t[0]
        return None

    def db_last_index(self):
        """
        (Overrides) Filter results by Phabricator instance

        Returns:
            the largest indexable value of all instance repos in the db
        """
        t = self.db_session.query(func.max(self.MODEL.indexable))
        t = t.filter(self.MODEL.instance == self.instance).first()
        if t:
            return t[0]

    def db_query_range(self, start: int, end: int):
        """
        (Overrides) Filter the results by the Phabricator instance to
        avoid disabling loading tasks for repositories hosted on a
        different instance.

        Returns:
            a list of sqlalchemy.ext.declarative.declarative_base objects
                with indexable values within the given range for the instance
        """
        retlist = super().db_query_range(start, end)
        return retlist.filter(self.MODEL.instance == self.instance)


def get_repo_url(attachments: List[Dict[str, Any]]) -> Optional[int]:
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
