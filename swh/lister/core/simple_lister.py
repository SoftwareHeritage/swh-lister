# Copyright (C) 2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import abc
import logging

from swh.core import utils

from .lister_base import SWHListerBase


class SimpleLister(SWHListerBase):
    """Lister* intermediate class for any service that follows the simple,
       'list in oneshot information' pattern.

    - Client sends a request to list repositories in oneshot

    - Client receives structured (json/xml/etc) response with
      information and stores those in db

    """
    @abc.abstractmethod
    def list_packages(self, *args):
        """Listing packages method.

        """
        pass

    def ingest_data(self, identifier, checks=False):
        """Rework the base ingest_data.
           Request server endpoint which gives all in one go.

           Simplify and filter response list of repositories.  Inject
           repo information into local db. Queue loader tasks for
           linked repositories.

        Args:
            identifier: Resource identifier (unused)
            checks (bool): Additional checks required (unused)

        """
        response = self.safely_issue_request(identifier)
        response = self.list_packages(response)
        if not response:
            return response, []
        models_list = self.transport_response_simplified(response)
        models_list = self.filter_before_inject(models_list)
        all_injected = []
        for models in utils.grouper(models_list, n=10000):
            models = list(models)
            logging.debug('models: %s' % len(models))
            # inject into local db
            injected = self.inject_repo_data_into_db(models)
            # queue workers
            self.create_missing_origins_and_tasks(models, injected)
            all_injected.append(injected)
            # flush
            self.db_session.commit()
            self.db_session = self.mk_session()

        return response, all_injected

    def run(self):
        """Query the server which answers in one query.  Stores the
           information, dropping actual redundant information we
           already have.

        Returns:
            nothing

        """
        dump_not_used_identifier = 0
        response, injected_repos = self.ingest_data(dump_not_used_identifier)
        if not response and not injected_repos:
            logging.info('No response from api server, stopping')
