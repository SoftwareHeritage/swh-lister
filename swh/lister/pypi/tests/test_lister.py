# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import requests_mock
import unittest
from unittest.mock import patch
from swh.lister.pypi.lister import PyPILister
from swh.lister.core.tests.test_lister import HttpSimpleListerTester

lister = PyPILister()

expected_packages = ['0lever-so', '0lever-utils', '0-orchestrator', '0wned']

expected_model = {
            'uid': 'arrow',
            'name': 'arrow',
            'full_name': 'arrow',
            'html_url': 'https://pypi.org/pypi/arrow/json',
            'origin_url': 'https://pypi.org/project/arrow/',
            'origin_type': 'pypi',
        }


class PyPIListerTester(HttpSimpleListerTester, unittest.TestCase):
    Lister = PyPILister
    PAGE = 'https://pypi.org/simple/'
    lister_subdir = 'pypi'
    good_api_response_file = 'api_response.html'
    entries = 4

    @requests_mock.Mocker()
    def test_list_packages(self, http_mocker):
        """List packages from simple api page should retrieve all packages within

        """
        http_mocker.get(self.PAGE, text=self.mock_response)
        fl = self.get_fl()
        packages = fl.list_packages(self.get_api_response(0))

        for package in expected_packages:
            assert package in packages

    def test_transport_response_simplified(self):
        """Test model created by the lister

        """
        fl = self.get_fl()
        model = fl.transport_response_simplified(['arrow'])
        assert len(model) == 1
        for key, values in model[0].items():
            assert values == expected_model[key]

    def test_task_dict(self):
        """Test the task creation of lister

        """
        with patch('swh.lister.pypi.lister.utils.create_task_dict') as mock_create_tasks:   # noqa
            lister.task_dict(origin_type='pypi', origin_url='https://abc',
                             name='test_pack', html_url='https://def')

        mock_create_tasks.assert_called_once_with(
            'load-pypi', 'recurring', 'test_pack', 'https://abc',
            project_metadata_url='https://def')
