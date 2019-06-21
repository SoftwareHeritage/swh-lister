# Copyright (C) 2017-2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import datetime
import logging
import iso8601

from urllib import parse

from swh.lister.bitbucket.models import BitBucketModel
from swh.lister.core.indexing_lister import IndexingHttpLister


logger = logging.getLogger(__name__)


class BitBucketLister(IndexingHttpLister):
    PATH_TEMPLATE = '/repositories?after=%s'
    MODEL = BitBucketModel
    LISTER_NAME = 'bitbucket'
    instance = 'bitbucket'

    def get_model_from_repo(self, repo):
        return {
            'uid': repo['uuid'],
            'indexable': repo['created_on'],
            'name': repo['name'],
            'full_name': repo['full_name'],
            'html_url': repo['links']['html']['href'],
            'origin_url': repo['links']['clone'][0]['href'],
            'origin_type': repo['scm'],
        }

    def get_next_target_from_response(self, response):
        body = response.json()
        if 'next' in body:
            return parse.unquote(body['next'].split('after=')[1])

    def transport_response_simplified(self, response):
        repos = response.json()['values']
        return [self.get_model_from_repo(repo) for repo in repos]

    def db_first_index(self):
        """For the first time listing, there is no data in db, so fallback to the
        bitbucket starting year.

        """
        return super().db_first_index() or '2008-01-01T00:00:00Z'

    def db_last_index(self):
        """For the first time listing, there is no data in db, so fallback to the time
           of the first run as max date.

        """
        return super().db_last_index() or datetime.datetime.now(
            tz=datetime.timezone.utc).isoformat()

    def request_uri(self, identifier):
        return super().request_uri(identifier or '1970-01-01')

    def is_within_bounds(self, inner, lower=None, upper=None):
        # values are expected to be str dates
        try:
            inner = iso8601.parse_date(inner)
            if lower:
                lower = iso8601.parse_date(lower)
            if upper:
                upper = iso8601.parse_date(upper)
            if lower is None and upper is None:
                return True
            elif lower is None:
                ret = inner <= upper
            elif upper is None:
                ret = inner >= lower
            else:
                ret = lower <= inner <= upper
        except Exception as e:
            logger.error(str(e) + ': %s, %s, %s' %
                         (('inner=%s%s' % (type(inner), inner)),
                          ('lower=%s%s' % (type(lower), lower)),
                          ('upper=%s%s' % (type(upper), upper)))
                         )
            raise

        return ret
