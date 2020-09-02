# Copyright (C) 2017-2020 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

# import random

from celery import shared_task

from .lister import LaunchpadLister


@shared_task(name=__name__ + ".IncrementalLaunchpadLister")
def launchpad_lister_incremental(threshold, **lister_args):
    """Incremental update
    """
    lister = LaunchpadLister(**lister_args)
    return lister.run(max_bound=threshold)


@shared_task(name=__name__ + ".FullLaunchpadLister", bind=True)
def list_launchpad_full(self, **lister_args):
    """Full update of Launchpad
    """
    self.log.debug("%s OK, spawned full task" % (self.name))
    return launchpad_lister_incremental(threshold=None, **lister_args)


@shared_task(name=__name__ + ".NewLaunchpadLister", bind=True)
def list_launchpad_new(self, **lister_args):
    """Update new entries of Launchpad
    """
    lister = LaunchpadLister(**lister_args)
    threshold = lister.db_last_threshold()
    self.log.debug("%s OK, spawned new task" % (self.name))
    return launchpad_lister_incremental(threshold=threshold, **lister_args)
