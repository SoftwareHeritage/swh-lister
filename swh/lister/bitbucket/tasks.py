# Copyright (C) 2017 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.lister.core.tasks import (IndexingDiscoveryListerTask,
                                   IndexingRangeListerTask,
                                   IndexingRefreshListerTask, ListerTaskBase)

from .lister import BitBucketLister


class BitBucketListerTask(ListerTaskBase):
    def new_lister(self):
        return BitBucketLister(lister_name='bitbucket.com',
                               api_baseurl='https://api.bitbucket.org/2.0')


class IncrementalBitBucketLister(BitBucketListerTask,
                                 IndexingDiscoveryListerTask):
    task_queue = 'swh_lister_bitbucket_discover'


class RangeBitBucketLister(BitBucketListerTask, IndexingRangeListerTask):
    task_queue = 'swh_lister_bitbucket_refresh'


class FullBitBucketRelister(BitBucketListerTask, IndexingRefreshListerTask):
    task_queue = 'swh_lister_bitbucket_refresh'
