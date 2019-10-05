# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json
import logging
import pkg_resources
import subprocess

from collections import defaultdict
from typing import List, Dict

from swh.lister.cran.models import CRANModel

from swh.lister.core.simple_lister import SimpleLister
from swh.scheduler.utils import create_task_dict


logger = logging.getLogger(__name__)


class CRANLister(SimpleLister):
    MODEL = CRANModel
    LISTER_NAME = 'cran'
    instance = 'cran'
    descriptions = defaultdict(dict)

    def task_dict(self, origin_type, origin_url, **kwargs):
        """Return task format dict

        This is overridden from the lister_base as more information is
        needed for the ingestion task creation.
        """
        return create_task_dict(
            'load-%s' % origin_type,
            kwargs.get('policy', 'recurring'),
            kwargs.get('name'), origin_url, kwargs.get('version'),
            project_metadata=self.descriptions[kwargs.get('name')])

    def safely_issue_request(self, identifier: str) -> List[Dict]:
        """Runs R script which uses inbuilt API to return a json response
           containing data about all the R packages.

        Returns:
            List of Dict about r packages.

        Sample:
            [
              {
                'Package': 'A3',
                'Version': '1.0.0',
                'Title':
                    'Accurate, Adaptable, and Accessible Error Metrics for
                     Predictive\nModels',
                'Description':
                    'Supplies tools for tabulating and analyzing the results
                     of predictive models. The methods employed are ... '
              },
              {
                'Package': 'abbyyR',
                'Version': '0.5.4',
                'Title':
                    'Access to Abbyy Optical Character Recognition (OCR) API',
                'Description': 'Get text from images of text using Abbyy
                                Cloud Optical Character\n ...'
               },
                ...
            ]

        """
        filepath = pkg_resources.resource_filename('swh.lister.cran',
                                                   'list_all_packages.R')
        logger.debug('script list-all-packages.R path: %s', filepath)
        response = subprocess.run(
            filepath, stdout=subprocess.PIPE, shell=False)
        data = json.loads(response.stdout)
        logger.debug('r-script-request: %s', data)
        return data

    def get_model_from_repo(self, repo):
        """Transform from repository representation to model

        """
        self.descriptions[repo["Package"]] = repo['Description']
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
        }
