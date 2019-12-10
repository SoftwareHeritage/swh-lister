# Copyright (C) 2017-2019 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging
import iso8601

from datetime import datetime, timezone
from typing import Any
from urllib import parse


from swh.lister.bitbucket.models import BitBucketModel
from swh.lister.core.indexing_lister import IndexingHttpLister


logger = logging.getLogger(__name__)


class BitBucketLister(IndexingHttpLister):
    PATH_TEMPLATE = '/repositories?after=%s'
    MODEL = BitBucketModel
    LISTER_NAME = 'bitbucket'
    DEFAULT_URL = 'https://api.bitbucket.org/2.0'
    instance = 'bitbucket'
    default_min_bound = datetime.fromtimestamp(0, timezone.utc)  # type: Any

    def __init__(self, url=None, override_config=None, per_page=100):
        super().__init__(url=url, override_config=override_config)
        per_page = self.config.get('per_page', per_page)

        self.PATH_TEMPLATE = '%s&pagelen=%s' % (
            self.PATH_TEMPLATE, per_page)

    def get_model_from_repo(self, repo):
        return {
            'uid': repo['uuid'],
            'indexable': iso8601.parse_date(repo['created_on']),
            'name': repo['name'],
            'full_name': repo['full_name'],
            'html_url': repo['links']['html']['href'],
            'origin_url': repo['links']['clone'][0]['href'],
            'origin_type': repo['scm'],
        }

    def get_next_target_from_response(self, response):
        """This will read the 'next' link from the api response if any
           and return it as a datetime.

        Args:
            response (Response): requests' response from api call

        Returns:
            next date as a datetime

        """
        body = response.json()
        next_ = body.get('next')
        if next_ is not None:
            next_ = parse.urlparse(next_)
            return iso8601.parse_date(parse.parse_qs(next_.query)['after'][0])

    def transport_response_simplified(self, response):
        repos = response.json()['values']
        return [self.get_model_from_repo(repo) for repo in repos]

    def request_uri(self, identifier):
        identifier = parse.quote(identifier.isoformat())
        return super().request_uri(identifier or '1970-01-01')

    def is_within_bounds(self, inner, lower=None, upper=None):
        # values are expected to be datetimes
        if lower is None and upper is None:
            ret = True
        elif lower is None:
            ret = inner <= upper
        elif upper is None:
            ret = inner >= lower
        else:
            ret = lower <= inner <= upper
        return ret
