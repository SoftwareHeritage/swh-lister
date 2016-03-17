# Copyright © 2016 The Software Heritage Developers <swh-devel@inria.fr>
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from math import ceil
import time

from . import github_api, req_queue, storage_utils


class ProcessError(ValueError):
    pass


def repositories(item, queue, session, credentials, storage):
    print('Processing scrolling repositories %s' % item['url'])
    repos = github_api.repositories(url=item['url'], session=session,
                                    credentials=credentials)
    if not repos['code'] == 200:
        raise ProcessError(item)

    if 'next' in repos['links']:
        req_queue.push(queue, {
            'type': 'repositories',
            'url': repos['links']['next']['url'],
        })

    users = {}
    for repo in repos['data']:
        users[repo['owner']['id']] = repo['owner']

    for id, user in users.items():
        jid = 'user-%d' % id
        if not queue.client.jobs[jid]:
            req_queue.push(queue, {
                'type': 'user',
                'user_login': user['login'],
                'user_id': id,
            }, jid=jid)

    for repo in repos['data']:
        if not repo['fork']:
            req_queue.push(queue, {
                'type': 'repository',
                'repo_name': repo['full_name'],
                'repo_id': repo['id'],
            })

    storage_utils.update_repo_entities(storage, repos['data'])


def repository(item, queue, session, credentials, storage):
    print('Processing repository %s (%s)' % (item['repo_name'],
                                             item['repo_id']))

    last_modified = storage_utils.repo_last_modified(storage, item['repo_id'])
    data = github_api.repository(item['repo_id'], session, credentials,
                                 last_modified)

    print(last_modified, '/', data['last_modified'])
    if data['code'] == 304:
        print('not modified')
        # Not modified
        # XXX: add validity
        return
    elif data['code'] == 200:
        print('modified')
        storage_utils.update_repo_entities(storage, [data['data']])
        if data['data']['forks']:
            npages = ceil(data['data']['forks']/30)
            for page in range(1, npages + 1):
                req_queue.push(queue, {
                    'type': 'forks',
                    'repo_id': item['repo_id'],
                    'repo_name': item['repo_name'],
                    'forks_page': page,
                    'check_next': page == npages,
                })
        return
    else:
        print('Could not get reply for repository %s' % item['repo_name'])
        print(data)


def forks(item, queue, session, credentials, storage):
    print('Processing forks for repository %s (%s, page %s)' % (
        item['repo_name'], item['repo_id'], item['forks_page']))

    forks = github_api.forks(item['repo_id'], item['forks_page'], session,
                             credentials)

    users = {}
    for repo in forks['data']:
        users[repo['owner']['id']] = repo['owner']

    for id, user in users.items():
        jid = 'user-%d' % id
        if not queue.client.jobs[jid]:
            req_queue.push(queue, {
                'type': 'user',
                'user_login': user['login'],
                'user_id': id,
            }, jid=jid)

    if item['check_next'] and 'next' in forks['links']:
        req_queue.push(queue, {
            'type': 'forks',
            'repo_id': item['repo_id'],
            'repo_name': item['repo_name'],
            'forks_page': item['forks_page'] + 1,
            'check_next': True,
        })

    storage_utils.update_repo_entities(storage, forks['data'])


def user(item, queue, session, credentials, storage):
    print('Processing user %s (%s)' % (item['user_login'], item['user_id']))

    last_modified = storage_utils.user_last_modified(storage, item['user_id'])

    data = github_api.user(item['user_id'], session, credentials,
                           last_modified)

    print(last_modified, '/', data['last_modified'])
    if data['code'] == 304:
        print('not modified')
        # Not modified
        # XXX: add validity
        return
    elif data['code'] == 200:
        print('modified')
        storage_utils.update_user_entities(storage, [data['data']])
        return
    else:
        print('Could not get reply for user %s' % item['user_login'])
        print(data)

PROCESSORS = {
    'repositories': repositories,
    'repository': repository,
    'forks': forks,
    'user': user,
}


def process_one_item(queue, session, credentials, storage):

    job = None

    while True:
        job = req_queue.pop(queue)
        if job:
            break
        time.sleep(0.1)

    try:
        PROCESSORS[job.klass_name](job.data, queue, session, credentials,
                                   storage)
    except Exception:
        raise
    else:
        job.complete()
