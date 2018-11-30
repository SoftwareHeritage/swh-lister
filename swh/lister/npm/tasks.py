# Copyright (C) 2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from datetime import datetime

from swh.lister.core.tasks import ListerTaskBase
from swh.lister.npm.lister import NpmLister, NpmIncrementalLister
from swh.lister.npm.models import NpmVisitModel


class _NpmListerTaskBase(ListerTaskBase):

    task_queue = 'swh_lister_npm_refresh'

    def _save_registry_state(self):
        """Query the root endpoint from the npm registry and
        backup values of interest for future listing
        """
        params = {'headers': self.lister.request_headers()}
        registry_state = \
            self.lister.session.get(self.lister.api_baseurl, **params)
        registry_state = registry_state.json()
        self.registry_state = {
            'visit_date': datetime.now(),
        }
        for key in ('doc_count', 'doc_del_count', 'update_seq', 'purge_seq',
                    'disk_size', 'data_size', 'committed_update_seq',
                    'compacted_seq'):
            self.registry_state[key] = registry_state[key]

    def _store_registry_state(self):
        """Store the backup npm registry state to database.
        """
        npm_visit = NpmVisitModel(**self.registry_state)
        self.lister.db_session.add(npm_visit)
        self.lister.db_session.commit()


class NpmListerTask(_NpmListerTaskBase):
    """Full npm lister (list all available packages from the npm registry)
    """

    def new_lister(self):
        return NpmLister()

    def run_task(self):
        self.lister = self.new_lister()
        self._save_registry_state()
        self.lister.run()
        self._store_registry_state()


class NpmIncrementalListerTask(_NpmListerTaskBase):
    """Incremental npm lister (list all updated packages since the last listing)
    """

    def new_lister(self):
        return NpmIncrementalLister()

    def run_task(self):
        self.lister = self.new_lister()
        update_seq_start = self._get_last_update_seq()
        self._save_registry_state()
        self.lister.run(min_bound=update_seq_start)
        self._store_registry_state()

    def _get_last_update_seq(self):
        """Get latest ``update_seq`` value for listing only updated packages.
        """
        query = self.lister.db_session.query(NpmVisitModel.update_seq)
        row = query.order_by(NpmVisitModel.uid.desc()).first()
        if not row:
            raise ValueError('No npm registry listing previously performed ! '
                             'This is required prior to the execution of an '
                             'incremental listing.')
        return row[0]
