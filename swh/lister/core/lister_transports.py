# Copyright (C) 2017 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import abc
import random
from datetime import datetime
from email.utils import parsedate
from pprint import pformat

import requests
import xmltodict

from .abstractattribute import AbstractAttribute
from .lister_base import FetchError


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

    def request_headers(self):
        """Returns dictionary of any request headers needed by the server.

        MAY BE OVERRIDDEN if request headers are needed.
        """
        return {}

    def transport_quota_check(self, response):
        """Implements SWHListerBase.transport_quota_check with standard 429 code
            check for HTTP with Requests library.

        MAY BE OVERRIDDEN if the server notifies about rate limits in a
            non-standard way that doesn't use HTTP 429 and the Retry-After
            response header. ( https://tools.ietf.org/html/rfc6585#section-4 )
        """
        if response.status_code == 429:  # HTTP too many requests
            retry_after = response.headers.get('Retry-After', self.back_off())
            try:
                # might be seconds
                return True, float(retry_after)
            except:
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

    def transport_request(self, identifier):
        """Implements SWHListerBase.transport_request for HTTP using Requests.
        """
        path = self.PATH_TEMPLATE % identifier
        params = {}
        params['headers'] = self.request_headers() or {}
        creds = self.config['credentials']
        auth = random.choice(creds) if creds else None
        if auth:
            params['auth'] = auth
        try:
            return self.session.get(self.api_baseurl + path, **params)
        except requests.exceptions.ConnectionError as e:
            raise FetchError(e)

    def transport_response_to_string(self, response):
        """Implements SWHListerBase.transport_response_to_string for HTTP given
            Requests responses.
        """
        s = pformat(response.request.path_url)
        s += '\n#\n' + pformat(response.status_code)
        s += '\n#\n' + pformat(response.headers)
        s += '\n#\n'
        try:  # json?
            s += pformat(response.json())
        except:  # not json
            try:  # xml?
                s += pformat(xmltodict.parse(response.text))
            except:  # not xml
                s += pformat(response.text)
        return s
