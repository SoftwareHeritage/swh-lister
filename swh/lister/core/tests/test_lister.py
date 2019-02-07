# Copyright (C) 2017-2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import abc
import time
from unittest import TestCase
from unittest.mock import Mock, patch

import requests_mock
from sqlalchemy import create_engine
from testing.postgresql import Postgresql

from swh.lister.core.abstractattribute import AbstractAttribute


def noop(*args, **kwargs):
    pass


@requests_mock.Mocker()
class HttpListerTesterBase(abc.ABC):
    """Base testing class for subclasses of

           swh.lister.core.indexing_lister.SWHIndexingHttpLister.
           swh.lister.core.page_by_page_lister.PageByPageHttpLister

    See swh.lister.github.tests.test_gh_lister for an example of how
    to customize for a specific listing service.

    """
    Lister = AbstractAttribute('The lister class to test')
    test_re = AbstractAttribute('Compiled regex matching the server url. Must'
                                ' capture the index value.')
    lister_subdir = AbstractAttribute('bitbucket, github, etc.')
    good_api_response_file = AbstractAttribute('Example good response body')
    bad_api_response_file = AbstractAttribute('Example bad response body')
    first_index = AbstractAttribute('First index in good_api_response')
    entries_per_page = AbstractAttribute('Number of results in good response')
    LISTER_NAME = 'fake-lister'

    # May need to override this if the headers are used for something
    def response_headers(self, request):
        return {}

    # May need to override this if the server uses non-standard rate limiting
    # method.
    # Please keep the requested retry delay reasonably low.
    def mock_rate_quota(self, n, request, context):
        self.rate_limit += 1
        context.status_code = 429
        context.headers['Retry-After'] = '1'
        return '{"error":"dummy"}'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rate_limit = 1
        self.response = None
        self.fl = None
        self.helper = None
        if self.__class__ != HttpListerTesterBase:
            self.run = TestCase.run.__get__(self, self.__class__)
        else:
            self.run = noop

    def request_index(self, request):
        m = self.test_re.search(request.path_url)
        if m and (len(m.groups()) > 0):
            return m.group(1)
        else:
            return None

    def mock_response(self, request, context):
        self.fl.reset_backoff()
        self.rate_limit = 1
        context.status_code = 200
        custom_headers = self.response_headers(request)
        context.headers.update(custom_headers)
        if self.request_index(request) == str(self.first_index):
            with open('swh/lister/%s/tests/%s' % (self.lister_subdir,
                                                  self.good_api_response_file),
                      'r', encoding='utf-8') as r:
                return r.read()
        else:
            with open('swh/lister/%s/tests/%s' % (self.lister_subdir,
                                                  self.bad_api_response_file),
                      'r', encoding='utf-8') as r:
                return r.read()

    def mock_limit_n_response(self, n, request, context):
        self.fl.reset_backoff()
        if self.rate_limit <= n:
            return self.mock_rate_quota(n, request, context)
        else:
            return self.mock_response(request, context)

    def mock_limit_once_response(self, request, context):
        return self.mock_limit_n_response(1, request, context)

    def mock_limit_twice_response(self, request, context):
        return self.mock_limit_n_response(2, request, context)

    def get_fl(self, override_config=None):
        """Retrieve an instance of fake lister (fl).

        """
        if override_config or self.fl is None:
            self.fl = self.Lister(api_baseurl='https://fakeurl',
                                  override_config=override_config)
            self.fl.INITIAL_BACKOFF = 1

        self.fl.reset_backoff()
        return self.fl

    def get_api_response(self):
        fl = self.get_fl()
        if self.response is None:
            self.response = fl.safely_issue_request(self.first_index)
        return self.response

    def test_is_within_bounds(self, http_mocker):
        fl = self.get_fl()
        self.assertFalse(fl.is_within_bounds(1, 2, 3))
        self.assertTrue(fl.is_within_bounds(2, 1, 3))
        self.assertTrue(fl.is_within_bounds(1, 1, 1))
        self.assertTrue(fl.is_within_bounds(1, None, None))
        self.assertTrue(fl.is_within_bounds(1, None, 2))
        self.assertTrue(fl.is_within_bounds(1, 0, None))
        self.assertTrue(fl.is_within_bounds("b", "a", "c"))
        self.assertFalse(fl.is_within_bounds("a", "b", "c"))
        self.assertTrue(fl.is_within_bounds("a", None, "c"))
        self.assertTrue(fl.is_within_bounds("a", None, None))
        self.assertTrue(fl.is_within_bounds("b", "a", None))
        self.assertFalse(fl.is_within_bounds("a", "b", None))
        self.assertTrue(fl.is_within_bounds("aa:02", "aa:01", "aa:03"))
        self.assertFalse(fl.is_within_bounds("aa:12", None, "aa:03"))
        with self.assertRaises(TypeError):
            fl.is_within_bounds(1.0, "b", None)
        with self.assertRaises(TypeError):
            fl.is_within_bounds("A:B", "A::B", None)

    def test_api_request(self, http_mocker):
        http_mocker.get(self.test_re, text=self.mock_limit_twice_response)
        with patch.object(time, 'sleep', wraps=time.sleep) as sleepmock:
            self.get_api_response()
            self.assertEqual(sleepmock.call_count, 2)

    def test_repos_list(self, http_mocker):
        http_mocker.get(self.test_re, text=self.mock_response)
        li = self.get_fl().transport_response_simplified(
            self.get_api_response()
        )
        self.assertIsInstance(li, list)
        self.assertEqual(len(li), self.entries_per_page)

    def test_model_map(self, http_mocker):
        http_mocker.get(self.test_re, text=self.mock_response)
        fl = self.get_fl()
        li = fl.transport_response_simplified(self.get_api_response())
        di = li[0]
        self.assertIsInstance(di, dict)
        pubs = [k for k in vars(fl.MODEL).keys() if not k.startswith('_')]
        for k in pubs:
            if k not in ['last_seen', 'task_id', 'origin_id', 'id']:
                self.assertIn(k, di)

    def disable_storage_and_scheduler(self, fl):
        fl.create_missing_origins_and_tasks = Mock(return_value=None)

    def disable_db(self, fl):
        fl.winnow_models = Mock(return_value=[])
        fl.db_inject_repo = Mock(return_value=fl.MODEL())
        fl.disable_deleted_repo_tasks = Mock(return_value=None)

    def test_fetch_none_nodb(self, http_mocker):
        http_mocker.get(self.test_re, text=self.mock_response)
        fl = self.get_fl()

        self.disable_storage_and_scheduler(fl)
        self.disable_db(fl)

        fl.run(min_bound=1, max_bound=1)  # stores no results

    def test_fetch_one_nodb(self, http_mocker):
        http_mocker.get(self.test_re, text=self.mock_response)
        fl = self.get_fl()

        self.disable_storage_and_scheduler(fl)
        self.disable_db(fl)

        fl.run(min_bound=self.first_index, max_bound=self.first_index)

    def test_fetch_multiple_pages_nodb(self, http_mocker):
        http_mocker.get(self.test_re, text=self.mock_response)
        fl = self.get_fl()

        self.disable_storage_and_scheduler(fl)
        self.disable_db(fl)

        fl.run(min_bound=self.first_index)

    def init_db(self, db, model):
        engine = create_engine(db.url())
        model.metadata.create_all(engine)


class HttpListerTester(HttpListerTesterBase, abc.ABC):
    last_index = AbstractAttribute('Last index in good_api_response')

    @requests_mock.Mocker()
    def test_fetch_multiple_pages_yesdb(self, http_mocker):
        http_mocker.get(self.test_re, text=self.mock_response)
        initdb_args = Postgresql.DEFAULT_SETTINGS['initdb_args']
        initdb_args = ' '.join([initdb_args, '-E UTF-8'])
        db = Postgresql(initdb_args=initdb_args)

        fl = self.get_fl(override_config={
            'lister': {
                'cls': 'local',
                'args': {'db': db.url()}
                }
            })
        self.init_db(db, fl.MODEL)

        self.disable_storage_and_scheduler(fl)

        fl.run(min_bound=self.first_index)

        self.assertEqual(fl.db_last_index(), self.last_index)
        partitions = fl.db_partition_indices(5)
        self.assertGreater(len(partitions), 0)
        for k in partitions:
            self.assertLessEqual(len(k), 5)
            self.assertGreater(len(k), 0)
