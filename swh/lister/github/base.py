# Copyright (C) 2016 The Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.core import config
from swh.storage import get_storage
from swh.scheduler.backend import SchedulerBackend


# TODO: split this into a lister-agnostic module

class SWHLister(config.SWHConfig):
    CONFIG_BASE_FILENAME = None

    DEFAULT_CONFIG = {
        'storage_class': ('str', 'remote_storage'),
        'storage_args': ('list[str]', ['http://localhost:5000/']),

        'scheduling_db': ('str', 'dbname=softwareheritage-scheduler'),
    }

    ADDITIONAL_CONFIG = {}

    def __init__(self):
        self.config = self.parse_config_file(
            additional_configs=[self.ADDITIONAL_CONFIG])

        self.storage = get_storage(self.config['storage_class'],
                                   self.config['storage_args'])

        self.scheduler = SchedulerBackend(
            scheduling_db=self.config['scheduling_db'],
        )

    def create_origins(self, origins):
        """Create the origins listed, and return their ids.

        Args:
            origins: a list of origins
        Returns:
            a list of origin ids
        """
        return self.storage.origin_add(origins)

    def create_tasks(self, tasks):
        """Create the tasks specified, and return their ids.

        Args:
            tasks (list of dict): a list of task specifications:
                type (str): the task type
                arguments (dict): the arguments for the task runner
                    args (list of str): arguments
                    kwargs (dict str -> str): keyword arguments
                next_run (datetime.datetime): when to schedule the next run
        Returns:
            a list of task ids
        """
        returned_tasks = self.scheduler.create_tasks(tasks)
        return [returned_task['id'] for returned_task in returned_tasks]

    def disable_tasks(self, task_ids):
        """Disable the tasks identified by the given ids"""
        self.scheduler.disable_tasks(task_ids)
