# Copyright © 2016 The Software Heritage Developers <swh-devel@inria.fr>
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import redis

cache = None


def init_cache(url):
    global cache
    cache = redis.StrictRedis.from_url(url, decode_responses=True)


def _user_key(id):
    return 'github:user:%d:uuid' % id


def _repo_key(id):
    return 'github:repo:%d:uuid' % id


def get_user(id):
    """Get the cache value for user `id`"""
    return cache.get(_user_key(id))


def set_user(id, uuid):
    """Set the cache value for user `id`"""
    cache.set(_user_key(id), uuid)


def get_repo(id):
    """Get the cache value for repo `id`"""
    return cache.get(_repo_key(id))


def set_repo(id, uuid):
    """Set the cache value for repo `id`"""
    return cache.set(_repo_key(id), uuid)
