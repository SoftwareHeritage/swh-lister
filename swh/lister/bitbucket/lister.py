# Copyright (C) 2017-2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from urllib import parse

from swh.lister.bitbucket.models import BitBucketModel
from swh.lister.core.indexing_lister import SWHIndexingHttpLister


class BitBucketLister(SWHIndexingHttpLister):
    PATH_TEMPLATE = '/repositories?after=%s'
    MODEL = BitBucketModel
    LISTER_NAME = 'bitbucket.com'

    def get_model_from_repo(self, repo):
        return {
            'uid': repo['uuid'],
            'indexable': repo['created_on'],
            'name': repo['name'],
            'full_name': repo['full_name'],
            'html_url': repo['links']['html']['href'],
            'origin_url': repo['links']['clone'][0]['href'],
            'origin_type': repo['scm'],
            'description': repo['description']
        }

    def get_next_target_from_response(self, response):
        body = response.json()
        if 'next' in body:
            return parse.unquote(body['next'].split('after=')[1])
        else:
            return None

    def transport_response_simplified(self, response):
        repos = response.json()['values']
        return [self.get_model_from_repo(repo) for repo in repos]
