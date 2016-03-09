# Copyright © 2016 The Software Heritage Developers <swh-devel@inria.fr>
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os

import requests

from swh.core.config import load_named_config, prepare_folders
from swh.storage import get_storage

from . import req_queue, processors

DEFAULT_CONFIG = {
    'queue_file': ('str', '~/.cache/swh/lister-github/queue.pickle'),
    'storage_class': ('str', 'local_storage'),
    'storage_args': ('list[str]', ['dbname=softwareheritage-dev',
                                   '/srv/softwareheritage/objects']),
    'credentials': ('list[str]', []),

}
CONFIG_NAME = 'lister/github.ini'


def run_from_queue():
    config = load_named_config(CONFIG_NAME, DEFAULT_CONFIG)

    queue_file = os.path.expanduser(config['queue_file'])
    prepare_folders(os.path.dirname(queue_file))

    credentials = {}
    for credential in config['credentials']:
        login, token = credential.split(':')
        credentials[login] = {'token': token}

    queue = req_queue.restore_from_file(queue_file)

    if req_queue.empty(queue):
        req_queue.push(queue, {'type': 'repositories', 'url': None})

    session = requests.Session()
    storage = get_storage(config['storage_class'], config['storage_args'])

    try:
        while not req_queue.empty(queue):
            processors.process_one_item(
                queue, session=session, credentials=credentials,
                storage=storage
            )

    finally:
        req_queue.dump_to_file(queue, queue_file)
