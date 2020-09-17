# Copyright (C) 2015-2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import abc
from datetime import datetime
from itertools import count
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

import dateutil
from requests import Response
from sqlalchemy import func

from .lister_base import ListerBase
from .lister_transports import ListerHttpTransport

logger = logging.getLogger(__name__)


class IndexingLister(ListerBase):
    """Lister* intermediate class for any service that follows the pattern:

    - The service must report at least one stable unique identifier, known
      herein as the UID value, for every listed repository.
    - If the service splits the list of repositories into sublists, it must
      report at least one stable and sorted index identifier for every listed
      repository, known herein as the indexable value, which can be used as
      part of the service endpoint query to request a sublist beginning from
      that index. This might be the UID if the UID is monotonic.
    - Client sends a request to list repositories starting from a given
      index.
    - Client receives structured (json/xml/etc) response with information about
      a sequential series of repositories starting from that index and, if
      necessary/available, some indication of the URL or index for fetching the
      next series of repository data.

    See :class:`swh.lister.core.lister_base.ListerBase` for more details.

    This class cannot be instantiated. To create a new Lister for a source
    code listing service that follows the model described above, you must
    subclass this class and provide the required overrides in addition to
    any unmet implementation/override requirements of this class's base.
    (see parent class and member docstrings for details)

    Required Overrides::

        def get_next_target_from_response

    """

    flush_packet_db = 20
    """Number of iterations in-between write flushes of lister repositories to
       db (see fn:`run`).
    """
    default_min_bound = ""
    """Default initialization value for the minimum boundary index to use when
       undefined (see fn:`run`).
    """

    @abc.abstractmethod
    def get_next_target_from_response(
        self, response: Response
    ) -> Union[Optional[datetime], Optional[str], Optional[int]]:
        """Find the next server endpoint identifier given the entire response.

        Implementation of this method depends on the server API spec
        and the shape of the network response object returned by the
        transport_request method.

        Args:
            response (transport response): response page from the server
        Returns:
            index of next page, possibly extracted from a next href url
        """
        pass

    # You probably don't need to override anything below this line.

    def filter_before_inject(
        self, models_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Overrides ListerBase.filter_before_inject

        Bounds query results by this Lister's set max_index.
        """
        models_list = [
            m
            for m in models_list
            if self.is_within_bounds(m["indexable"], None, self.max_index)
        ]
        return models_list

    def db_query_range(self, start, end):
        """Look in the db for a range of repositories with indexable
            values in the range [start, end]

        Args:
            start (model indexable type): start of desired indexable range
            end (model indexable type): end of desired indexable range
        Returns:
            a list of sqlalchemy.ext.declarative.declarative_base objects
                with indexable values within the given range
        """
        retlist = self.db_session.query(self.MODEL)
        if start is not None:
            retlist = retlist.filter(self.MODEL.indexable >= start)
        if end is not None:
            retlist = retlist.filter(self.MODEL.indexable <= end)
        return retlist

    def db_partition_indices(
        self, partition_size: int
    ) -> List[Tuple[Optional[int], Optional[int]]]:
        """Describe an index-space compartmentalization of the db table
           in equal sized chunks. This is used to describe min&max bounds for
           parallelizing fetch tasks.

        Args:
            partition_size (int): desired size to make each partition

        Returns:
            a list of tuples (begin, end) of indexable value that
            declare approximately equal-sized ranges of existing
            repos

        """
        n = max(self.db_num_entries(), 10)
        partition_size = min(partition_size, n)
        n_partitions = n // partition_size

        min_index = self.db_first_index()
        max_index = self.db_last_index()

        if min_index is None or max_index is None:
            # Nothing to list
            return []

        if isinstance(min_index, str):

            def format_bound(bound):
                return bound.isoformat()

            min_index = dateutil.parser.parse(min_index)
            max_index = dateutil.parser.parse(max_index)
        elif isinstance(max_index - min_index, int):

            def format_bound(bound):
                return int(bound)

        else:

            def format_bound(bound):
                return bound

        partition_width = (max_index - min_index) / n_partitions

        # Generate n_partitions + 1 bounds for n_partitions partitons
        bounds = [
            format_bound(min_index + i * partition_width)
            for i in range(n_partitions + 1)
        ]

        # Trim duplicate bounds
        bounds.append(None)
        bounds = [cur for cur, next in zip(bounds[:-1], bounds[1:]) if cur != next]

        # Remove bounds for lowest and highest partition
        bounds[0] = bounds[-1] = None

        return list(zip(bounds[:-1], bounds[1:]))

    def db_first_index(self):
        """Look in the db for the smallest indexable value

        Returns:
            the smallest indexable value of all repos in the db
        """
        t = self.db_session.query(func.min(self.MODEL.indexable)).first()
        if t:
            return t[0]
        return None

    def db_last_index(self):
        """Look in the db for the largest indexable value

        Returns:
            the largest indexable value of all repos in the db
        """
        t = self.db_session.query(func.max(self.MODEL.indexable)).first()
        if t:
            return t[0]
        return None

    def disable_deleted_repo_tasks(self, start, end, keep_these):
        """Disable tasks for repos that no longer exist between start and end.

        Args:
            start: beginning of range to disable
            end: end of range to disable
            keep_these (uid list): do not disable repos with uids in this list
        """
        if end is None:
            end = self.db_last_index()

        if not self.is_within_bounds(end, None, self.max_index):
            end = self.max_index

        deleted_repos = self.winnow_models(
            self.db_query_range(start, end), self.MODEL.uid, keep_these
        )
        tasks_to_disable = [
            repo.task_id for repo in deleted_repos if repo.task_id is not None
        ]
        if tasks_to_disable:
            self.scheduler.disable_tasks(tasks_to_disable)
        for repo in deleted_repos:
            repo.task_id = None

    def run(self, min_bound=None, max_bound=None):
        """Main entry function. Sequentially fetches repository data
            from the service according to the basic outline in the class
            docstring, continually fetching sublists until either there
            is no next index reference given or the given next index is greater
            than the desired max_bound.

        Args:
            min_bound (indexable type): optional index to start from
            max_bound (indexable type): optional index to stop at
        Returns:
            nothing
        """
        status = "uneventful"
        self.min_index = min_bound
        self.max_index = max_bound

        def ingest_indexes():
            index = min_bound or self.default_min_bound
            for i in count(1):
                response, injected_repos = self.ingest_data(index)
                if not response and not injected_repos:
                    logger.info("No response from api server, stopping")
                    return

                next_index = self.get_next_target_from_response(response)
                # Determine if any repos were deleted, and disable their tasks.
                keep_these = list(injected_repos.keys())
                self.disable_deleted_repo_tasks(index, next_index, keep_these)

                # termination condition
                if next_index is None or next_index == index:
                    logger.info("stopping after index %s, no next link found", index)
                    return
                index = next_index
                logger.debug("Index: %s", index)
                yield i

        for i in ingest_indexes():
            if (i % self.flush_packet_db) == 0:
                logger.debug("Flushing updates at index %s", i)
                self.db_session.commit()
                self.db_session = self.mk_session()
                status = "eventful"

        self.db_session.commit()
        self.db_session = self.mk_session()
        return {"status": status}


class IndexingHttpLister(ListerHttpTransport, IndexingLister):
    """Convenience class for ensuring right lookup and init order
        when combining IndexingLister and ListerHttpTransport."""

    def __init__(self, url=None, override_config=None):
        IndexingLister.__init__(self, override_config=override_config)
        ListerHttpTransport.__init__(self, url=url)
