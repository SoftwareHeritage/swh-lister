# Copyright © 2016 The Software Heritage Developers <swh-devel@inria.fr>
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from collections import defaultdict, deque
import os
import pickle
import tempfile

PRIORITIES = {
    'forks': 10,
    'user': 15,
    'repository': 20,
    'repositories': 30,
}


def restore_from_file(file):
    if not os.path.exists(file):
        return defaultdict(deque)

    with open(file, 'rb') as f:
        return pickle.load(f)


def dump_to_file(queue, file):
    fd, filename = tempfile.mkstemp(dir=os.path.dirname(file))
    with open(fd, 'wb') as f:
        pickle.dump(queue, f)
        f.flush()
        os.fsync(fd)
    os.rename(filename, file)


def push(queue, item):
    queue[item['type']].append(item)


def push_front(queue, item):
    queue[item['type']].appendleft(item)


def pop(queue):
    for type in sorted(queue, key=lambda t: PRIORITIES.get(t, 1000)):
        if queue[type]:
            return queue[type].popleft()

    raise IndexError("No items to pop")


def empty(queue):
    return not queue
