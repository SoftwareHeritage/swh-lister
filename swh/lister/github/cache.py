# Copyright © 2016 The Software Heritage Developers <swh-devel@inria.fr>
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


GITHUB_USER_UUID_CACHE = {}
GITHUB_REPO_UUID_CACHE = {}


def get_user(id):
    """Get the cache value for user `id`"""
    return GITHUB_USER_UUID_CACHE.get(id)


def set_user(id, uuid):
    """Set the cache value for user `id`"""
    GITHUB_USER_UUID_CACHE[id] = uuid


def get_repo(id):
    """Get the cache value for repo `id`"""
    return GITHUB_REPO_UUID_CACHE.get(id)


def set_repo(id, uuid):
    """Set the cache value for repo `id`"""
    GITHUB_REPO_UUID_CACHE[id] = uuid
