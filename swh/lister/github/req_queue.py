# Copyright © 2016 The Software Heritage Developers <swh-devel@inria.fr>
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import qless


PRIORITIES = {
    'forks': 100,
    'repository': 75,
    'user': 50,
    'repositories': 40,
}


def from_url(url):
    return qless.Client(url).queues['github-lister']


def push(queue, item, **kwargs):
    print("Push %s to %s" % (item, queue.name))
    type = item.pop('type')
    queue.put(type, item, priority=PRIORITIES.get(type, 0), **kwargs)


def pop(queue):
    return queue.pop()


def empty(queue):
    return not len(queue)
