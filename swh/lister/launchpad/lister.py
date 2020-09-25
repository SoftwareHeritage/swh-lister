# Copyright (C) 2017-2020 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from datetime import datetime, timedelta
from itertools import count
from typing import Any, Dict, List, Optional, Tuple, Union

from launchpadlib.launchpad import Launchpad  # type: ignore
from lazr.restfulclient.resource import Collection, Entry  # type: ignore
from sqlalchemy import func

from swh.lister.core.lister_base import ListerBase

from .models import LaunchpadModel


class LaunchpadLister(ListerBase):
    MODEL = LaunchpadModel
    LISTER_NAME = "launchpad"
    instance = "launchpad"
    launchpad: Launchpad
    flush_packet_db = 20

    def __init__(self, override_config=None):
        super().__init__(override_config=override_config)
        self.launchpad = Launchpad.login_anonymously(
            "softwareheritage", "production", version="devel"
        )

    def get_model_from_repo(self, repo: Entry) -> Dict[str, Union[str, datetime]]:
        return {
            "uid": repo.unique_name,
            "name": repo.name,
            "full_name": repo.name,
            "origin_url": repo.git_https_url,
            "html_url": repo.web_link,
            "origin_type": "git",
            "date_last_modified": repo.date_last_modified,
        }

    def lib_response_simplified(
        self, response: Collection
    ) -> List[Dict[str, Union[str, datetime]]]:
        return [
            self.get_model_from_repo(repo) for repo in response[: len(response.entries)]
        ]

    def get_git_repos(self, threshold: Optional[datetime]) -> Collection:
        get_repos = self.launchpad.git_repositories.getRepositories

        return get_repos(order_by="most neglected first", modified_since_date=threshold)

    def db_last_threshold(self) -> Optional[datetime]:
        t = self.db_session.query(func.max(self.MODEL.date_last_modified)).first()
        if t:
            return t[0]
        else:
            return None

    def ingest_data_lp(
        self, identifier: Optional[datetime], checks: bool = False
    ) -> Tuple[Collection, dict]:
        """ The core data fetch sequence. Request launchpadlib endpoint. Simplify and
            filter response list of repositories. Inject repo information into
            local db. Queue loader tasks for linked repositories.

        Args:
            identifier: Resource identifier.
            checks: Additional checks required
        """
        response = self.get_git_repos(identifier)
        models_list = self.lib_response_simplified(response)
        models_list = self.filter_before_inject(models_list)
        if checks:
            models_list = self.do_additional_checks(models_list)
            if not models_list:
                return response, {}
        # inject into local db
        injected = self.inject_repo_data_into_db(models_list)
        # queue workers
        self.schedule_missing_tasks(models_list, injected)
        return response, injected

    def run(self, max_bound: Optional[datetime] = None) -> Dict[str, Any]:
        """ Main entry function. Sequentially fetches repository data
            from the service according to the basic outline in the class
            docstring, continually fetching sublists until either there
            is no next index reference given or the given next index is greater
            than the desired max_bound.

        Args:
            max_bound : optional date to start at
        Returns:
            Dict containing listing status
        """
        status = "uneventful"

        def ingest_git_repos():
            threshold = max_bound
            for i in count(1):
                response, injected_repos = self.ingest_data_lp(threshold)
                if not response and not injected_repos:
                    return

                # batch is empty
                if len(response.entries) == 0:
                    return

                first: datetime = response[0].date_last_modified
                last: datetime = response[len(response.entries) - 1].date_last_modified

                next_date = last - timedelta(seconds=15)

                if next_date <= first:
                    delta = last - first
                    next_date = last - delta / 2

                threshold = next_date
                yield i

        for i in ingest_git_repos():
            if (i % self.flush_packet_db) == 0:
                self.db_session.commit()
                self.db_session = self.mk_session()
                status = "eventful"

        self.db_session.commit()
        self.db_session = self.mk_session()
        return {"status": status}
