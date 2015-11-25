# Copyright (C) 2015  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import psycopg2
import pickle


def list_imported_repos(swh_db):
    """List all the repositories that have been successfully imported in Software
    Heritage.
    """
    query = """
    select o.url
    from origin o
    left join fetch_history fh
    on o.id = fh.origin
    where
        fh.status = true and
        o.url ~~ 'https://github.com/%'
    """

    cur = swh_db.cursor()
    cur.execute(query)
    res = cur.fetchall()
    cur.close()
    return set('/'.join(repo.rsplit('/', 2)[-2:]) for (repo,) in res)


def list_fetched_repos(ghlister_db):
    """List all the repositories that have been successfully fetched from GitHub.
    """
    query = """
    select r.full_name
    from crawl_history ch
    left join repos r
    on ch.repo = r.id
    where
        ch.status = true and
        r.fork = false
    """

    cur = ghlister_db.cursor()
    cur.execute(query)
    res = cur.fetchall()
    cur.close()
    return set(repo for (repo,) in res)


def list_missing_repos():
    """List all the repositories that have not yet been imported successfully."""
    swh_db = psycopg2.connect('service=softwareheritage')
    imported_repos = list_imported_repos(swh_db)
    swh_db.close()

    ghlister_db = psycopg2.connect('service=lister-github')
    fetched_repos = list_fetched_repos(ghlister_db)
    ghlister_db.close()

    return fetched_repos - imported_repos


def generate_tasks(checkpoint_file='repos', checkpoint_every=100000):
    """Generate the Celery tasks to fetch all the missing repositories.

    Checkpoint the missing repositories every checkpoint_every tasks sent, in a
    pickle file called checkpoint_file.

    If the checkpoint file exists, we do not call the database again but load
    from the file.
    """
    import swh.loader.git.tasks
    from swh.core.worker import app  # flake8: noqa for side effects

    def checkpoint_repos(repos, checkpoint=checkpoint_file):
        tmp = '.%s.tmp' % checkpoint
        with open(tmp, 'wb') as f:
            pickle.dump(repos, f)

        os.rename(tmp, checkpoint)

    def fetch_checkpoint_repos(checkpoint=checkpoint_file):
        with open(checkpoint, 'rb') as f:
            return pickle.load(f)

    repos = set()

    if not os.path.exists(checkpoint_file):
        repos = list_missing_repos()
        checkpoint_repos(repos)
    else:
        repos = fetch_checkpoint_repos()

    task = app.tasks['swh.loader.git.tasks.LoadGitHubRepository']

    ctr = 0
    while True:
        try:
            repo = repos.pop()
        except KeyError:
            break

        task.delay(repo)

        ctr += 1
        if ctr >= checkpoint_every:
            ctr = 0
            checkpoint_repos(repos)

    os.unlink(checkpoint)
