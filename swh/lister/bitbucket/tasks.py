# Copyright (C) 2017-2021 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Optional

from celery import shared_task

from .lister import BitbucketLister


@shared_task(name=__name__ + ".IncrementalBitBucketLister")
def list_bitbucket_incremental(
    page_size: Optional[int] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
):
    """Incremental listing of the public Bitbucket repositories."""
    lister = BitbucketLister.from_configfile(page_size=page_size, incremental=True)
    lister.set_credentials(username, password)
    return lister.run().dict()


@shared_task(name=__name__ + ".FullBitBucketRelister")
def list_bitbucket_full(
    page_size: Optional[int] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
):
    """Full listing of the public Bitbucket repositories."""
    lister = BitbucketLister.from_configfile(page_size=page_size, incremental=False)
    lister.set_credentials(username, password)
    return lister.run().dict()


@shared_task(name=__name__ + ".ping")
def _ping():
    return "OK"
