# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


from swh.lister.core.indexing_lister import SWHIndexingHttpLister
from swh.lister.phabricator.models import PhabricatorModel
from collections import defaultdict


class PhabricatorLister(SWHIndexingHttpLister):

    PATH_TEMPLATE = '&order=oldest&attachments[uris]=1&after=%s'
    MODEL = PhabricatorModel
    LISTER_NAME = 'phabricator'

    def __init__(self, forge_url, api_token, override_config=None):
        if forge_url.endswith("/"):
            forge_url = forge_url[:-1]
        self.forge_url = forge_url
        api_endpoint = ('api/diffusion.repository.'
                        'search?api.token=%s') % api_token
        api_baseurl = '%s/%s' % (forge_url, api_endpoint)
        super().__init__(api_baseurl=api_baseurl,
                         override_config=override_config)

    def request_headers(self):
        """
        (Override) Set requests headers to send when querying the
        Phabricator API
        """
        return {'User-Agent': 'Software Heritage phabricator lister',
                'Accept': 'application/json'}

    def get_model_from_repo(self, repo):
        url = get_repo_url(repo['attachments']['uris']['uris'])
        if url is None:
            return None
        return {
            'uid': self.forge_url + str(repo['id']),
            'indexable': repo['id'],
            'name': repo['fields']['shortName'],
            'full_name': repo['fields']['name'],
            'html_url': url,
            'origin_url': url,
            'description': None,
            'origin_type': repo['fields']['vcs']
        }

    def get_next_target_from_response(self, response):
        body = response.json()['result']['cursor']
        if body['after'] != 'null':
            return body['after']
        else:
            return None

    def transport_response_simplified(self, response):
        repos = response.json()
        if repos['result'] is None:
            raise ValueError(
                'Problem during information fetch: %s' % repos['error_code'])
        repos = repos['result']['data']
        return [self.get_model_from_repo(repo) for repo in repos]

    def filter_before_inject(self, models_list):
        """
        (Overrides) SWHIndexingLister.filter_before_inject
        Bounds query results by this Lister's set max_index.
        """
        models_list = [m for m in models_list if m is not None]
        return super().filter_before_inject(models_list)

    def _bootstrap_repositories_listing(self):
        """
        Method called when no min_bound value has been provided
        to the lister. Its purpose is to:

            1. get the first repository data hosted on the Phabricator
               instance

            2. inject them into the lister database

            3. return the first repository index to start the listing
               after that value

        Returns:
             int: The first repository index
        """
        params = '&order=oldest&limit=1'
        response = self.safely_issue_request(params)
        models_list = self.transport_response_simplified(response)
        self.max_index = models_list[0]['indexable']
        models_list = self.filter_before_inject(models_list)
        injected = self.inject_repo_data_into_db(models_list)
        self.create_missing_origins_and_tasks(models_list, injected)
        return self.max_index

    def run(self, min_bound=None, max_bound=None):
        """
        (Override) Run the lister on the specified Phabricator instance

        Args:
            min_bound (int): Optional repository index to start the listing
                after it
            max_bound (int): Optional repository index to stop the listing
                after it
        """
        # initial call to the lister, we need to bootstrap it in that case
        if min_bound is None:
            min_bound = self._bootstrap_repositories_listing()
        super().run(min_bound, max_bound)


def get_repo_url(attachments):
    """
    Return url for a hosted repository from its uris attachments according
    to the following priority lists:
    * protocol: https > http
    * identifier: shortname > callsign > id
    """
    processed_urls = defaultdict(dict)
    for uri in attachments:
        protocol = uri['fields']['builtin']['protocol']
        url = uri['fields']['uri']['effective']
        identifier = uri['fields']['builtin']['identifier']
        if protocol in ('http', 'https'):
            processed_urls[protocol][identifier] = url
        elif protocol is None:
            for protocol in ('https', 'http'):
                if url.startswith(protocol):
                    processed_urls[protocol]['undefined'] = url
                break
    for protocol in ['https', 'http']:
        for identifier in ['shortname', 'callsign', 'id', 'undefined']:
            if (protocol in processed_urls and
                    identifier in processed_urls[protocol]):
                return processed_urls[protocol][identifier]
    return None
