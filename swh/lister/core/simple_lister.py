# Copyright (C) 2018-2019 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging
from typing import Any, List

from swh.core import utils

from .lister_base import ListerBase

logger = logging.getLogger(__name__)


class SimpleLister(ListerBase):
    """Lister* intermediate class for any service that follows the simple,
       'list in oneshot information' pattern.

    - Client sends a request to list repositories in oneshot

    - Client receives structured (json/xml/etc) response with
      information and stores those in db

    """

    flush_packet_db = 2
    """Number of iterations in-between write flushes of lister repositories to
       db (see fn:`ingest_data`).
    """

    def list_packages(self, response: Any) -> List[Any]:
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
        for i, models in enumerate(utils.grouper(models_list, n=100), start=1):
            models = list(models)
            logging.debug("models: %s" % len(models))
            # inject into local db
            injected = self.inject_repo_data_into_db(models)
            # queue workers
            self.schedule_missing_tasks(models, injected)
            all_injected.append(injected)
            if (i % self.flush_packet_db) == 0:
                logger.debug("Flushing updates at index %s", i)
                self.db_session.commit()
                self.db_session = self.mk_session()

        return response, all_injected

    def transport_response_simplified(self, response):
        """Transform response to list for model manipulation

        """
        return [self.get_model_from_repo(repo_name) for repo_name in response]

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
            logging.info("No response from api server, stopping")
            status = "uneventful"
        else:
            status = "eventful"

        return {"status": status}
