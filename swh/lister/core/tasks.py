# Copyright (C) 2017 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import abc
import random

from celery import group
from celery.app.task import TaskType

from swh.scheduler.task import Task

from .abstractattribute import AbstractAttribute


class AbstractTaskMeta(abc.ABCMeta, TaskType):
    pass


class ListerTaskBase(Task, metaclass=AbstractTaskMeta):
    """Lister Tasks define the process of periodically requesting batches of
        repository information from source code hosting services. They
        instantiate Listers to do batches of work at periodic intervals.

        There are two main kinds of lister tasks:

            1) Discovering new repositories.
            2) Refreshing the list of already discovered repositories.

        If the hosting service is indexable (according to the requirements of
        SWHIndexingLister), then we can optionally partition the set of known
        repositories into sub-sets to distribute the work.

        This means that there is a third possible Task type for Indexing
        Listers:
            3) Discover or refresh a specific range of indices.
    """
    task_queue = AbstractAttribute('Celery Task queue name')

    @abc.abstractmethod
    def new_lister(self):
        """Return a new lister of the appropriate type.
        """
        pass

    @abc.abstractmethod
    def run_task(self):
        pass


class IndexingDiscoveryListerTask(ListerTaskBase):
    def run_task(self):
        lister = self.new_lister()
        return lister.run(min_index=lister.db_last_index(), max_index=None)


class IndexingRangeListerTask(ListerTaskBase):
    def run_task(self, start, end):
        lister = self.new_lister()
        return lister.run(min_index=start, max_index=end)


class IndexingRefreshListerTask(ListerTaskBase):
    GROUP_SPLIT = 10000

    def run_task(self):
        lister = self.new_lister()
        ranges = lister.db_partition_indices(self.GROUP_SPLIT)
        random.shuffle(ranges)
        range_task = IndexingRangeListerTask()
        group(range_task.s(minv, maxv) for minv, maxv in ranges)()
