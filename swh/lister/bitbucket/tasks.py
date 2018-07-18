# Copyright (C) 2017-2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.lister.core.tasks import (IndexingDiscoveryListerTask,
                                   RangeListerTask,
                                   IndexingRefreshListerTask, ListerTaskBase)

from .lister import BitBucketLister


class BitBucketListerTask(ListerTaskBase):
    def new_lister(self, *, api_baseurl='https://api.bitbucket.org/2.0'):
        return BitBucketLister(api_baseurl=api_baseurl)


class IncrementalBitBucketLister(BitBucketListerTask,
                                 IndexingDiscoveryListerTask):
    task_queue = 'swh_lister_bitbucket_discover'


class RangeBitBucketLister(BitBucketListerTask, RangeListerTask):
    task_queue = 'swh_lister_bitbucket_refresh'


class FullBitBucketRelister(BitBucketListerTask, IndexingRefreshListerTask):
    task_queue = 'swh_lister_bitbucket_refresh'
