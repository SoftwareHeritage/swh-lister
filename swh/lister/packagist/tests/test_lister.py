# Copyright (C) 2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import unittest
from unittest.mock import patch

import requests_mock

from swh.lister.core.tests.test_lister import HttpSimpleListerTester
from swh.lister.packagist.lister import PackagistLister, compute_package_url

expected_packages = [
    "0.0.0/composer-include-files",
    "0.0.0/laravel-env-shim",
    "0.0.1/try-make-package",
    "0099ff/dialogflowphp",
    "00f100/array_dot",
]

expected_model = {
    "uid": "0099ff/dialogflowphp",
    "name": "0099ff/dialogflowphp",
    "full_name": "0099ff/dialogflowphp",
    "html_url": "https://repo.packagist.org/p/0099ff/dialogflowphp.json",
    "origin_url": "https://repo.packagist.org/p/0099ff/dialogflowphp.json",
    "origin_type": "packagist",
}


class PackagistListerTester(HttpSimpleListerTester, unittest.TestCase):
    Lister = PackagistLister
    PAGE = "https://packagist.org/packages/list.json"
    lister_subdir = "packagist"
    good_api_response_file = "data/https_packagist.org/packages_list.json"
    entries = 5

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
        model = fl.transport_response_simplified(["0099ff/dialogflowphp"])
        assert len(model) == 1
        for key, values in model[0].items():
            assert values == expected_model[key]

    @patch("swh.lister.packagist.lister.utils.create_task_dict")
    def test_task_dict(self, mock_create_tasks):
        """Test the task creation of lister

        """
        fl = self.get_fl()
        fl.task_dict(
            origin_type="packagist", origin_url="https://abc", name="test_pack"
        )
        mock_create_tasks.assert_called_once_with(
            "load-packagist", "recurring", "test_pack", "https://abc", retries_left=3
        )


def test_compute_package_url():
    expected_url = "https://repo.packagist.org/p/hello.json"
    actual_url = compute_package_url("hello")
    assert actual_url == expected_url


def test_packagist_lister(lister_packagist, requests_mock_datadir):
    lister_packagist.run()

    r = lister_packagist.scheduler.search_tasks(task_type="load-packagist")
    assert len(r) == 5

    for row in r:
        assert row["type"] == "load-packagist"
        # arguments check
        args = row["arguments"]["args"]
        assert len(args) == 2

        package = args[0]
        url = args[1]

        expected_url = compute_package_url(package)
        assert url == expected_url

        # kwargs
        kwargs = row["arguments"]["kwargs"]
        assert kwargs == {}

        assert row["policy"] == "recurring"
        assert row["priority"] is None
