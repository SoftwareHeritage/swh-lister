# Copyright (C) 2017-2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import abc
import random

from celery import group

from swh.scheduler.task import Task, TaskType

from .abstractattribute import AbstractAttribute


class AbstractTaskMeta(abc.ABCMeta, TaskType):
    pass


class ListerTaskBase(Task, metaclass=AbstractTaskMeta):
    """Lister Tasks define the process of periodically requesting batches of
        repository information from source code hosting services. They
        instantiate Listers to do batches of work at periodic intervals.

        There are two main kinds of lister tasks:

        1. Discovering new repositories.
        2. Refreshing the list of already discovered repositories.

        If the hosting service is indexable (according to the requirements of
        :class:`SWHIndexingLister`), then we can optionally partition the
        set of known repositories into sub-sets to distribute the work.

        This means that there is a third possible Task type for Indexing
        Listers:

        3. Discover or refresh a specific range of indices.

    """
    task_queue = AbstractAttribute('Celery Task queue name')

    @abc.abstractmethod
    def new_lister(self, **lister_args):
        """Return a new lister of the appropriate type.
        """
        pass

    @abc.abstractmethod
    def run_task(self, *, lister_args=None):
        pass


# Paging/Indexing lister tasks derivatives
# (cf. {github/bitbucket/gitlab}/tasks)


class RangeListerTask(ListerTaskBase):
    """Range lister task.

    """
    def run_task(self, start, end, lister_args=None):
        if lister_args is None:
            lister_args = {}
        lister = self.new_lister(**lister_args)
        return lister.run(min_bound=start, max_bound=end)


# Indexing Lister tasks derivatives (cf. {github/bitbucket}/tasks)


class IndexingDiscoveryListerTask(ListerTaskBase):
    """Incremental indexing lister task.

    """
    def run_task(self, *, lister_args=None):
        if lister_args is None:
            lister_args = {}
        lister = self.new_lister(**lister_args)
        return lister.run(min_bound=lister.db_last_index(), max_bound=None)


class IndexingRefreshListerTask(ListerTaskBase):
    """Full indexing lister task.

    """
    GROUP_SPLIT = 10000

    def run_task(self, *, lister_args=None):
        if lister_args is None:
            lister_args = {}
        lister = self.new_lister(**lister_args)
        ranges = lister.db_partition_indices(self.GROUP_SPLIT)
        random.shuffle(ranges)
        range_task = RangeListerTask()
        group(range_task.s(minv, maxv, lister_args)
              for minv, maxv in ranges)()
