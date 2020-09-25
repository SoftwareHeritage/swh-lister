# Copyright (C) 2017-2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import abc
from datetime import datetime
from email.utils import parsedate
import logging
from pprint import pformat
import random
from typing import Any, Dict, List, Optional, Union

import requests
from requests import Response
import xmltodict

from swh.lister import USER_AGENT_TEMPLATE, __version__

from .abstractattribute import AbstractAttribute
from .lister_base import FetchError

logger = logging.getLogger(__name__)


class ListerHttpTransport(abc.ABC):
    """Use the Requests library for making Lister endpoint requests.

    To be used in conjunction with ListerBase or a subclass of it.
    """

    DEFAULT_URL = None  # type: Optional[str]
    PATH_TEMPLATE = AbstractAttribute(
        "string containing a python string format pattern that produces"
        " the API endpoint path for listing stored repositories when given"
        ' an index, e.g., "/repositories?after=%s". To be implemented in'
        " the API-specific class inheriting this."
    )  # type: Union[AbstractAttribute, Optional[str]]

    EXPECTED_STATUS_CODES = (200, 429, 403, 404)

    def request_headers(self) -> Dict[str, Any]:
        """Returns dictionary of any request headers needed by the server.

        MAY BE OVERRIDDEN if request headers are needed.
        """
        return {"User-Agent": USER_AGENT_TEMPLATE % self.lister_version}

    def request_instance_credentials(self) -> List[Dict[str, Any]]:
        """Returns dictionary of any credentials configuration needed by the
        forge instance to list.

        The 'credentials' configuration is expected to be a dict of multiple
        levels. The first level is the lister's name, the second is the
        lister's instance name, which value is expected to be a list of
        credential structures (typically a couple username/password).

        For example::

            credentials:
              github:  # github lister
                github:  # has only one instance (so far)
                  - username: some
                    password: somekey
                  - username: one
                    password: onekey
                  - ...
                gitlab:  # gitlab lister
                  riseup:  # has many instances
                    - username: someone
                      password: ...
                    - ...
                  gitlab:
                    - username: someone
                      password: ...
                    - ...

        Returns:
            list of credential dicts for the current lister.

        """
        all_creds = self.config.get("credentials")  # type: ignore
        if not all_creds:
            return []
        lister_creds = all_creds.get(self.LISTER_NAME, {})  # type: ignore
        creds = lister_creds.get(self.instance, [])  # type: ignore
        return creds

    def request_uri(self, identifier: str) -> str:
        """Get the full request URI given the transport_request identifier.

        MAY BE OVERRIDDEN if something more complex than the PATH_TEMPLATE is
        required.
        """
        path = self.PATH_TEMPLATE % identifier  # type: ignore
        return self.url + path

    def request_params(self, identifier: str) -> Dict[str, Any]:
        """Get the full parameters passed to requests given the
        transport_request identifier.

        This uses credentials if any are provided (see
        request_instance_credentials).

        MAY BE OVERRIDDEN if something more complex than the request headers
        is needed.

        """
        params = {}
        params["headers"] = self.request_headers() or {}
        creds = self.request_instance_credentials()
        if not creds:
            return params
        auth = random.choice(creds) if creds else None
        if auth:
            params["auth"] = (
                auth["username"],  # type: ignore
                auth["password"],
            )
        return params

    def transport_quota_check(self, response):
        """Implements ListerBase.transport_quota_check with standard 429
            code check for HTTP with Requests library.

        MAY BE OVERRIDDEN if the server notifies about rate limits in a
            non-standard way that doesn't use HTTP 429 and the Retry-After
            response header. ( https://tools.ietf.org/html/rfc6585#section-4 )

        """
        if response.status_code == 429:  # HTTP too many requests
            retry_after = response.headers.get("Retry-After", self.back_off())
            try:
                # might be seconds
                return True, float(retry_after)
            except Exception:
                # might be http-date
                at_date = datetime(*parsedate(retry_after)[:6])
                from_now = (at_date - datetime.today()).total_seconds() + 5
                return True, max(0, from_now)
        else:  # response ok
            self.reset_backoff()
            return False, 0

    def __init__(self, url=None):
        if not url:
            url = self.config.get("url")
        if not url:
            url = self.DEFAULT_URL
        if not url:
            raise NameError("HTTP Lister Transport requires an url.")
        self.url = url  # eg. 'https://api.github.com'
        self.session = requests.Session()
        self.lister_version = __version__

    def _transport_action(self, identifier: str, method: str = "get") -> Response:
        """Permit to ask information to the api prior to actually executing
           query.

        """
        path = self.request_uri(identifier)
        params = self.request_params(identifier)

        logger.debug("path: %s", path)
        logger.debug("params: %s", params)
        logger.debug("method: %s", method)
        try:
            if method == "head":
                response = self.session.head(path, **params)
            else:
                response = self.session.get(path, **params)
        except requests.exceptions.ConnectionError as e:
            logger.warning("Failed to fetch %s: %s", path, e)
            raise FetchError(e)
        else:
            if response.status_code not in self.EXPECTED_STATUS_CODES:
                raise FetchError(response)
            return response

    def transport_head(self, identifier: str) -> Response:
        """Retrieve head information on api.

        """
        return self._transport_action(identifier, method="head")

    def transport_request(self, identifier: str) -> Response:
        """Implements ListerBase.transport_request for HTTP using Requests.

        Retrieve get information on api.

        """
        return self._transport_action(identifier)

    def transport_response_to_string(self, response: Response) -> str:
        """Implements ListerBase.transport_response_to_string for HTTP given
            Requests responses.
        """
        s = pformat(response.request.path_url)
        s += "\n#\n" + pformat(response.request.headers)
        s += "\n#\n" + pformat(response.status_code)
        s += "\n#\n" + pformat(response.headers)
        s += "\n#\n"
        try:  # json?
            s += pformat(response.json())
        except Exception:  # not json
            try:  # xml?
                s += pformat(xmltodict.parse(response.text))
            except Exception:  # not xml
                s += pformat(response.text)
        return s


class ListerOnePageApiTransport(ListerHttpTransport):
    """Leverage requests library to retrieve basic html page and parse
       result.

       To be used in conjunction with ListerBase or a subclass of it.

    """

    PAGE = AbstractAttribute(
        "URL of the API's unique page to retrieve and parse " "for information"
    )  # type: Union[AbstractAttribute, str]
    PATH_TEMPLATE = None  # we do not use it

    def __init__(self, url=None):
        self.session = requests.Session()
        self.lister_version = __version__

    def request_uri(self, _):
        """Get the full request URI given the transport_request identifier.

        """
        return self.PAGE
