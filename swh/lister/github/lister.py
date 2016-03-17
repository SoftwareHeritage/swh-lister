# Copyright © 2016 The Software Heritage Developers <swh-devel@inria.fr>
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os

import requests

from swh.core.config import load_named_config
from swh.storage import get_storage

from . import req_queue, processors, cache

DEFAULT_CONFIG = {
    'queue_url': ('str', 'redis://localhost'),
    'cache_url': ('str', 'redis://localhost'),
    'storage_class': ('str', 'local_storage'),
    'storage_args': ('list[str]', ['dbname=softwareheritage-dev',
                                   '/srv/softwareheritage/objects']),
    'credentials': ('list[str]', []),

}
CONFIG_NAME = 'lister/github.ini'


def run_from_queue():
    config = load_named_config(CONFIG_NAME, DEFAULT_CONFIG)

    cache.init_cache(config['cache_url'])

    queue_url = os.path.expanduser(config['queue_url'])

    credentials = {}
    for credential in config['credentials']:
        login, token = credential.split(':')
        credentials[login] = {'token': token}

    queue = req_queue.from_url(queue_url)

    if req_queue.empty(queue):
        req_queue.push(queue, {'type': 'repositories', 'url': None})

    session = requests.Session()
    storage = get_storage(config['storage_class'], config['storage_args'])

    while not req_queue.empty(queue):
        processors.process_one_item(
            queue, session=session, credentials=credentials,
            storage=storage
        )

if __name__ == '__main__':
    run_from_queue()
