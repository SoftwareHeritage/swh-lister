# Copyright (C) 2017-2021  The Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Optional

from celery import shared_task

from .lister import BitbucketLister


@shared_task(name=__name__ + ".IncrementalBitBucketLister")
def list_bitbucket_incremental(
    username: Optional[str] = None,
    password: Optional[str] = None,
    **lister_args,
):
    """Incremental listing of Bitbucket repositories."""
    lister = BitbucketLister.from_configfile(incremental=True, **lister_args)
    lister.set_credentials(username, password)
    return lister.run().dict()


@shared_task(name=__name__ + ".FullBitBucketRelister")
def list_bitbucket_full(
    username: Optional[str] = None,
    password: Optional[str] = None,
    **lister_args,
):
    """Full listing of Bitbucket repositories."""
    lister = BitbucketLister.from_configfile(incremental=False, **lister_args)
    lister.set_credentials(username, password)
    return lister.run().dict()


@shared_task(name=__name__ + ".ping")
def _ping():
    return "OK"
