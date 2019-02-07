# Copyright (C) 2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from datetime import datetime
from contextlib import contextmanager

from swh.scheduler.celery_backend.config import app

from swh.lister.npm.lister import NpmLister, NpmIncrementalLister
from swh.lister.npm.models import NpmVisitModel


@contextmanager
def save_registry_state(lister):
    params = {'headers': lister.request_headers()}
    registry_state = lister.session.get(lister.api_baseurl, **params)
    registry_state = registry_state.json()
    keys = ('doc_count', 'doc_del_count', 'update_seq', 'purge_seq',
            'disk_size', 'data_size', 'committed_update_seq',
            'compacted_seq')

    state = {key: registry_state[key] for key in keys}
    state['visit_date'] = datetime.now()
    yield
    npm_visit = NpmVisitModel(**state)
    lister.db_session.add(npm_visit)
    lister.db_session.commit()


def get_last_update_seq(lister):
    """Get latest ``update_seq`` value for listing only updated packages.
    """
    query = lister.db_session.query(NpmVisitModel.update_seq)
    row = query.order_by(NpmVisitModel.uid.desc()).first()
    if not row:
        raise ValueError('No npm registry listing previously performed ! '
                         'This is required prior to the execution of an '
                         'incremental listing.')
    return row[0]


@app.task(name=__name__ + '.NpmListerTask')
def npm_lister(**lister_args):
    lister = NpmLister(**lister_args)
    with save_registry_state(lister):
        lister.run()


@app.task(name=__name__ + '.NpmIncrementalListerTask')
def npm_incremental_lister(**lister_args):
    lister = NpmIncrementalLister(**lister_args)
    update_seq_start = get_last_update_seq(lister)
    with save_registry_state(lister):
        lister.run(min_bound=update_seq_start)


@app.task(name=__name__ + '.ping')
def ping():
    return 'OK'
