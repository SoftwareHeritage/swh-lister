# Copyright (C) 2017-2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import abc
import random
from datetime import datetime
from email.utils import parsedate
from pprint import pformat
import logging

import requests
import xmltodict

try:
    from swh.lister._version import __version__
except ImportError:
    __version__ = 'devel'

from .abstractattribute import AbstractAttribute
from .lister_base import FetchError


logger = logging.getLogger(__name__)


class SWHListerHttpTransport(abc.ABC):
    """Use the Requests library for making Lister endpoint requests.

    To be used in conjunction with SWHListerBase or a subclass of it.
    """

    PATH_TEMPLATE = AbstractAttribute('string containing a python string'
                                      ' format pattern that produces the API'
                                      ' endpoint path for listing stored'
                                      ' repositories when given an index.'
                                      ' eg. "/repositories?after=%s".'
                                      'To be implemented in the API-specific'
                                      ' class inheriting this.')

    EXPECTED_STATUS_CODES = (200, 429, 403, 404)

    def request_headers(self):
        """Returns dictionary of any request headers needed by the server.

        MAY BE OVERRIDDEN if request headers are needed.
        """
        return {
            'User-Agent': 'Software Heritage lister (%s)' % self.lister_version
        }

    def request_uri(self, identifier):
        """Get the full request URI given the transport_request identifier.

        MAY BE OVERRIDDEN if something more complex than the PATH_TEMPLATE is
        required.
        """
        path = self.PATH_TEMPLATE % identifier
        return self.api_baseurl + path

    def request_params(self, identifier):
        """Get the full parameters passed to requests given the
        transport_request identifier.

        MAY BE OVERRIDDEN if something more complex than the request headers
        is needed.

        """
        params = {}
        params['headers'] = self.request_headers() or {}
        creds = self.config['credentials']
        auth = random.choice(creds) if creds else None
        if auth:
            params['auth'] = (auth['username'], auth['password'])
        return params

    def transport_quota_check(self, response):
        """Implements SWHListerBase.transport_quota_check with standard 429
            code check for HTTP with Requests library.

        MAY BE OVERRIDDEN if the server notifies about rate limits in a
            non-standard way that doesn't use HTTP 429 and the Retry-After
            response header. ( https://tools.ietf.org/html/rfc6585#section-4 )

        """
        if response.status_code == 429:  # HTTP too many requests
            retry_after = response.headers.get('Retry-After', self.back_off())
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

    def __init__(self, api_baseurl=None):
        if not api_baseurl:
            raise NameError('HTTP Lister Transport requires api_baseurl.')
        self.api_baseurl = api_baseurl  # eg. 'https://api.github.com'
        self.session = requests.Session()
        self.lister_version = __version__

    def _transport_action(self, identifier, method='get'):
        """Permit to ask information to the api prior to actually executing
           query.

        """
        path = self.request_uri(identifier)
        params = self.request_params(identifier)

        try:
            if method == 'head':
                response = self.session.head(path, **params)
            else:
                response = self.session.get(path, **params)
        except requests.exceptions.ConnectionError as e:
            logger.warning('Failed to fetch %s: %s', path, e)
            raise FetchError(e)
        else:
            if response.status_code not in self.EXPECTED_STATUS_CODES:
                raise FetchError(response)
            return response

    def transport_head(self, identifier):
        """Retrieve head information on api.

        """
        return self._transport_action(identifier, method='head')

    def transport_request(self, identifier):
        """Implements SWHListerBase.transport_request for HTTP using Requests.

        Retrieve get information on api.

        """
        return self._transport_action(identifier)

    def transport_response_to_string(self, response):
        """Implements SWHListerBase.transport_response_to_string for HTTP given
            Requests responses.
        """
        s = pformat(response.request.path_url)
        s += '\n#\n' + pformat(response.request.headers)
        s += '\n#\n' + pformat(response.status_code)
        s += '\n#\n' + pformat(response.headers)
        s += '\n#\n'
        try:  # json?
            s += pformat(response.json())
        except Exception:  # not json
            try:  # xml?
                s += pformat(xmltodict.parse(response.text))
            except Exception:  # not xml
                s += pformat(response.text)
        return s


class ListerOnePageApiTransport(SWHListerHttpTransport):
    """Leverage requests library to retrieve basic html page and parse
       result.

       To be used in conjunction with SWHListerBase or a subclass of it.

    """
    PAGE = AbstractAttribute("The server api's unique page to retrieve and "
                             "parse for information")
    PATH_TEMPLATE = None  # we do not use it

    def __init__(self, api_baseurl=None):
        self.session = requests.Session()
        self.lister_version = __version__

    def request_uri(self, _):
        """Get the full request URI given the transport_request identifier.

        """
        return self.PAGE
