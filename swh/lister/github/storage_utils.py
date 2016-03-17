# Copyright © 2016 The Software Heritage Developers <swh-devel@inria.fr>
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import uuid

from . import cache, constants, converters


def update_user_entities(storage, users):
    """Update entities for several users in storage. Returns the new entities.
    """

    users = list(sorted(users, key=lambda u: u['id']))

    query = [{
        'lister': constants.GITHUB_LISTER_UUID,
        'type': 'user',
        'id': user['id'],
    } for user in users]

    entities = list(storage.entity_get_from_lister_metadata(query))

    new_entities = []

    for user, entity in zip(users, entities):
        if not entity['uuid']:
            entity = {
                'uuid': uuid.uuid4(),
                'doap': {},
                'lister_metadata': {},
            }
        new_entity = converters.user_to_entity(entity, user)
        cache.set_user(user['id'], new_entity['uuid'])
        new_entities.append(new_entity)

    storage.entity_add(new_entities)

    return new_entities


def update_repo_entities(storage, repos):
    """Update entities for several repositories in storage. Returns the new
       entities."""

    repos = list(sorted(repos, key=lambda r: r['id']))

    users = {}
    for repo in repos:
        if not cache.get_user(repo['owner']['id']):
            users[repo['owner']['id']] = repo['owner']

    if users:
        update_user_entities(storage, users.values())

    query = [{
        'lister': constants.GITHUB_LISTER_UUID,
        'type': 'repository',
        'id': repo['id'],
    } for repo in repos]

    entities = list(storage.entity_get_from_lister_metadata(query))

    new_entities = []

    for repo, entity in zip(repos, entities):
        if not entity['uuid']:
            entity = {
                'uuid': uuid.uuid4(),
                'doap': {},
                'lister_metadata': {},
            }
            new_entities.append(converters.repository_to_entity(entity, repo))

    storage.entity_add(new_entities)

    return new_entities


def repo_last_modified(storage, id):
    entity_id = cache.get_repo(id)

    if entity_id:
        entity = storage.entity_get_one(entity_id)
    else:
        entity = list(storage.entity_get_from_lister_metadata([{
            'lister': constants.GITHUB_LISTER_UUID,
            'type': 'repository',
            'id': id,
        }]))[0]

        if entity['uuid']:
            cache.set_repo(id, entity['uuid'])

    updated_at = entity.get('lister_metadata', {}).get('updated_at')

    return converters.updated_at_to_last_modified(updated_at)


def user_last_modified(storage, id):
    entity_id = cache.get_user(id)

    if entity_id:
        entity = storage.entity_get_one(entity_id)
    else:
        entity = list(storage.entity_get_from_lister_metadata([{
            'lister': constants.GITHUB_LISTER_UUID,
            'type': 'user',
            'id': id,
        }]))[0]

        if entity['uuid']:
            cache.set_user(id, entity['uuid'])

    updated_at = entity.get('lister_metadata', {}).get('updated_at')

    return converters.updated_at_to_last_modified(updated_at)
