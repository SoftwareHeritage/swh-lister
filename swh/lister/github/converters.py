# Copyright © 2016 The Software Heritage Developers <swh-devel@inria.fr>
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import copy
import datetime
from email.utils import format_datetime

from dateutil.parser import parse as parse_datetime

from . import cache, storage_utils


def utcnow():
    return datetime.datetime.now(tz=datetime.timezone.utc)


def updated_at_to_last_modified(updated_at):
    if not updated_at:
        return None

    dt = parse_datetime(updated_at).astimezone(datetime.timezone.utc)
    return format_datetime(dt, usegmt=True)


def repository_to_entity(orig_entity, repo):
    """Convert a repository to an entity"""

    entity = copy.deepcopy(orig_entity)

    owner_uuid = cache.get_user(repo['owner']['id'])
    if not owner_uuid:
        raise ValueError("Owner %s (id=%d) not in cache" % (
            repo['owner']['login'], repo['owner']['id']))

    entity['parent'] = owner_uuid
    entity['name'] = repo['full_name']
    entity['type'] = 'project'
    entity['description'] = repo['description']
    if 'homepage' in repo:
        entity['homepage'] = repo['homepage']
    entity['active'] = True
    entity['generated'] = True

    entity['lister_metadata']['lister'] = storage_utils.GITHUB_LISTER_UUID
    entity['lister_metadata']['type'] = 'repository'
    entity['lister_metadata']['id'] = repo['id']
    entity['lister_metadata']['fork'] = repo['fork']

    if 'updated_at' in repo:
        entity['lister_metadata']['updated_at'] = repo['updated_at']

    entity['validity'] = [utcnow()]

    return entity


def user_to_entity(orig_entity, user):
    """Convert a GitHub user toan entity"""

    entity = copy.deepcopy(orig_entity)

    if user['type'] == 'User':
        parent = storage_utils.GITHUB_USERS_UUID
        type = 'person'
    elif user['type'] == 'Organization':
        parent = storage_utils.GITHUB_ORGS_UUID
        type = 'group_of_persons'
    else:
        raise ValueError("Unknown GitHub user type %s" % user['type'])

    entity['parent'] = parent

    if 'name' in user:
        entity['name'] = user['name']

    if not entity.get('name'):
        entity['name'] = user['login']

    entity['type'] = type
    entity['active'] = True
    entity['generated'] = True

    entity['lister_metadata']['lister'] = storage_utils.GITHUB_LISTER_UUID
    entity['lister_metadata']['type'] = 'user'
    entity['lister_metadata']['id'] = user['id']
    entity['lister_metadata']['login'] = user['login']

    if 'updated_at' in user:
        entity['lister_metadata']['updated_at'] = user['updated_at']

    entity['validity'] = [datetime.datetime.now()]

    return entity
