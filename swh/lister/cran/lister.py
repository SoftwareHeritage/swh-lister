# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information
import subprocess
import json
import logging
import pkg_resources

from swh.lister.cran.models import CRANModel

from swh.scheduler.utils import create_task_dict
from swh.core import utils
from swh.lister.core.simple_lister import SimpleLister


class CRANLister(SimpleLister):
    MODEL = CRANModel
    LISTER_NAME = 'cran'
    instance = 'cran'

    def task_dict(self, origin_type, origin_url, **kwargs):
        """Return task format dict

        This is overridden from the lister_base as more information is
        needed for the ingestion task creation.
        """
        return create_task_dict(
            'load-%s' % origin_type, 'recurring',
            kwargs.get('name'), origin_url, kwargs.get('version'),
            project_metadata=kwargs.get('description'))

    def r_script_request(self):
        """Runs R script which uses inbuilt API to return a json
            response containing data about all the R packages

        Returns:
            List of dictionaries
            example
            [
                {'Package': 'A3',
                'Version': '1.0.0',
                'Title':
                    'Accurate, Adaptable, and Accessible Error Metrics for
                     Predictive\nModels',
                'Description':
                    'Supplies tools for tabulating and analyzing the results
                     of predictive models. The methods employed are ... '
                }
                {'Package': 'abbyyR',
                'Version': '0.5.4',
                'Title':
                    'Access to Abbyy Optical Character Recognition (OCR) API',
                'Description': 'Get text from images of text using Abbyy
                                 Cloud Optical Character\n ...'
                }
                ...
            ]
        """
        file_path = pkg_resources.resource_filename('swh.lister.cran',
                                                    'list_all_packages.R')
        response = subprocess.run(file_path, stdout=subprocess.PIPE,
                                  shell=False)
        return json.loads(response.stdout)

    def get_model_from_repo(self, repo):
        """Transform from repository representation to model

        """
        project_url = 'https://cran.r-project.org/src/contrib' \
                      '/%(Package)s_%(Version)s.tar.gz' % repo
        return {
            'uid': repo["Package"],
            'name': repo["Package"],
            'full_name': repo["Title"],
            'version': repo["Version"],
            'html_url': project_url,
            'origin_url': project_url,
            'origin_type': 'cran',
            'description': repo["Description"]
        }

    def transport_response_simplified(self, response):
        """Transform response to list for model manipulation

        """
        return [self.get_model_from_repo(repo) for repo in response]

    def ingest_data(self, identifier, checks=False):
        """Rework the base ingest_data.
           Request server endpoint which gives all in one go.

           Simplify and filter response list of repositories.  Inject
           repo information into local db. Queue loader tasks for
           linked repositories.

        Args:
            identifier: Resource identifier (unused)
            checks (bool): Additional checks required (unused)

        """
        response = self.r_script_request()
        if not response:
            return response, []
        models_list = self.transport_response_simplified(response)
        models_list = self.filter_before_inject(models_list)
        all_injected = []
        for models in utils.grouper(models_list, n=10000):
            models = list(models)
            logging.debug('models: %s' % len(models))
            # inject into local db
            injected = self.inject_repo_data_into_db(models)
            # queue workers
            self.create_missing_origins_and_tasks(models, injected)
            all_injected.append(injected)
            # flush
            self.db_session.commit()
            self.db_session = self.mk_session()

        return response, all_injected
