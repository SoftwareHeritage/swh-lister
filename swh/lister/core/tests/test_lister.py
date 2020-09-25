# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import abc
import datetime
import time
from typing import Any, Callable, Optional, Pattern, Type, Union
from unittest import TestCase
from unittest.mock import Mock, patch

import requests_mock
from sqlalchemy import create_engine

import swh.lister
from swh.lister.core.abstractattribute import AbstractAttribute
from swh.lister.tests.test_utils import init_db


def noop(*args, **kwargs):
    pass


def test_version_generation():
    assert (
        swh.lister.__version__ != "devel"
    ), "Make sure swh.lister is installed (e.g. pip install -e .)"


class HttpListerTesterBase(abc.ABC):
    """Testing base class for listers.
       This contains methods for both :class:`HttpSimpleListerTester` and
       :class:`HttpListerTester`.

    See :class:`swh.lister.gitlab.tests.test_lister` for an example of how
    to customize for a specific listing service.

    """

    Lister = AbstractAttribute(
        "Lister class to test"
    )  # type: Union[AbstractAttribute, Type[Any]]
    lister_subdir = AbstractAttribute(
        "bitbucket, github, etc."
    )  # type: Union[AbstractAttribute, str]
    good_api_response_file = AbstractAttribute(
        "Example good response body"
    )  # type: Union[AbstractAttribute, str]
    LISTER_NAME = "fake-lister"

    # May need to override this if the headers are used for something
    def response_headers(self, request):
        return {}

    # May need to override this if the server uses non-standard rate limiting
    # method.
    # Please keep the requested retry delay reasonably low.
    def mock_rate_quota(self, n, request, context):
        self.rate_limit += 1
        context.status_code = 429
        context.headers["Retry-After"] = "1"
        return '{"error":"dummy"}'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rate_limit = 1
        self.response = None
        self.fl = None
        self.helper = None
        self.scheduler_tasks = []
        if self.__class__ != HttpListerTesterBase:
            self.run = TestCase.run.__get__(self, self.__class__)
        else:
            self.run = noop

    def mock_limit_n_response(self, n, request, context):
        self.fl.reset_backoff()
        if self.rate_limit <= n:
            return self.mock_rate_quota(n, request, context)
        else:
            return self.mock_response(request, context)

    def mock_limit_twice_response(self, request, context):
        return self.mock_limit_n_response(2, request, context)

    def get_api_response(self, identifier):
        fl = self.get_fl()
        if self.response is None:
            self.response = fl.safely_issue_request(identifier)
        return self.response

    def get_fl(self, override_config=None):
        """Retrieve an instance of fake lister (fl).

        """
        if override_config or self.fl is None:
            self.fl = self.Lister(
                url="https://fakeurl", override_config=override_config
            )
            self.fl.INITIAL_BACKOFF = 1

        self.fl.reset_backoff()
        self.scheduler_tasks = []
        return self.fl

    def disable_scheduler(self, fl):
        fl.schedule_missing_tasks = Mock(return_value=None)

    def mock_scheduler(self, fl):
        def _create_tasks(tasks):
            task_id = 0
            current_nb_tasks = len(self.scheduler_tasks)
            if current_nb_tasks > 0:
                task_id = self.scheduler_tasks[-1]["id"] + 1
            for task in tasks:
                scheduler_task = dict(task)
                scheduler_task.update(
                    {
                        "status": "next_run_not_scheduled",
                        "retries_left": 0,
                        "priority": None,
                        "id": task_id,
                        "current_interval": datetime.timedelta(days=64),
                    }
                )
                self.scheduler_tasks.append(scheduler_task)
                task_id = task_id + 1
            return self.scheduler_tasks[current_nb_tasks:]

        def _disable_tasks(task_ids):
            for task_id in task_ids:
                self.scheduler_tasks[task_id]["status"] = "disabled"

        fl.scheduler.create_tasks = Mock(wraps=_create_tasks)
        fl.scheduler.disable_tasks = Mock(wraps=_disable_tasks)

    def disable_db(self, fl):
        fl.winnow_models = Mock(return_value=[])
        fl.db_inject_repo = Mock(return_value=fl.MODEL())
        fl.disable_deleted_repo_tasks = Mock(return_value=None)

    def init_db(self, db, model):
        engine = create_engine(db.url())
        model.metadata.create_all(engine)

    @requests_mock.Mocker()
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


class HttpListerTester(HttpListerTesterBase, abc.ABC):
    """Base testing class for subclass of

           :class:`swh.lister.core.indexing_lister.IndexingHttpLister`

    See :class:`swh.lister.github.tests.test_gh_lister` for an example of how
    to customize for a specific listing service.

    """

    last_index = AbstractAttribute(
        "Last index " "in good_api_response"
    )  # type: Union[AbstractAttribute, int]
    first_index = AbstractAttribute(
        "First index in " " good_api_response"
    )  # type: Union[AbstractAttribute, Optional[int]]
    bad_api_response_file = AbstractAttribute(
        "Example bad response body"
    )  # type: Union[AbstractAttribute, str]
    entries_per_page = AbstractAttribute(
        "Number of results in " "good response"
    )  # type: Union[AbstractAttribute, int]
    test_re = AbstractAttribute(
        "Compiled regex matching the server url. Must capture the " "index value."
    )  # type: Union[AbstractAttribute, Pattern]
    convert_type = str  # type: Callable[..., Any]
    """static method used to convert the "request_index" to its right type (for
       indexing listers for example, this is in accordance with the model's
       "indexable" column).

    """

    def mock_response(self, request, context):
        self.fl.reset_backoff()
        self.rate_limit = 1
        context.status_code = 200
        custom_headers = self.response_headers(request)
        context.headers.update(custom_headers)
        req_index = self.request_index(request)

        if req_index == self.first_index:
            response_file = self.good_api_response_file
        else:
            response_file = self.bad_api_response_file

        with open(
            "swh/lister/%s/tests/%s" % (self.lister_subdir, response_file),
            "r",
            encoding="utf-8",
        ) as r:
            return r.read()

    def request_index(self, request):
        m = self.test_re.search(request.path_url)
        if m and (len(m.groups()) > 0):
            return self.convert_type(m.group(1))

    def create_fl_with_db(self, http_mocker):
        http_mocker.get(self.test_re, text=self.mock_response)
        db = init_db()

        fl = self.get_fl(
            override_config={"lister": {"cls": "local", "args": {"db": db.url()}}}
        )
        fl.db = db
        self.init_db(db, fl.MODEL)

        self.mock_scheduler(fl)
        return fl

    @requests_mock.Mocker()
    def test_fetch_no_bounds_yesdb(self, http_mocker):
        fl = self.create_fl_with_db(http_mocker)

        fl.run()

        self.assertEqual(fl.db_last_index(), self.last_index)
        ingested_repos = list(fl.db_query_range(self.first_index, self.last_index))
        self.assertEqual(len(ingested_repos), self.entries_per_page)

    @requests_mock.Mocker()
    def test_fetch_multiple_pages_yesdb(self, http_mocker):

        fl = self.create_fl_with_db(http_mocker)
        fl.run(min_bound=self.first_index)

        self.assertEqual(fl.db_last_index(), self.last_index)

        partitions = fl.db_partition_indices(5)
        self.assertGreater(len(partitions), 0)
        for k in partitions:
            self.assertLessEqual(len(k), 5)
            self.assertGreater(len(k), 0)

    @requests_mock.Mocker()
    def test_fetch_none_nodb(self, http_mocker):
        http_mocker.get(self.test_re, text=self.mock_response)
        fl = self.get_fl()

        self.disable_scheduler(fl)
        self.disable_db(fl)

        fl.run(min_bound=1, max_bound=1)  # stores no results
        # FIXME: Determine what this method tries to test and add checks to
        # actually test

    @requests_mock.Mocker()
    def test_fetch_one_nodb(self, http_mocker):
        http_mocker.get(self.test_re, text=self.mock_response)
        fl = self.get_fl()

        self.disable_scheduler(fl)
        self.disable_db(fl)

        fl.run(min_bound=self.first_index, max_bound=self.first_index)
        # FIXME: Determine what this method tries to test and add checks to
        # actually test

    @requests_mock.Mocker()
    def test_fetch_multiple_pages_nodb(self, http_mocker):
        http_mocker.get(self.test_re, text=self.mock_response)
        fl = self.get_fl()

        self.disable_scheduler(fl)
        self.disable_db(fl)

        fl.run(min_bound=self.first_index)
        # FIXME: Determine what this method tries to test and add checks to
        # actually test

    @requests_mock.Mocker()
    def test_repos_list(self, http_mocker):
        """Test the number of repos listed by the lister

        """
        http_mocker.get(self.test_re, text=self.mock_response)
        li = self.get_fl().transport_response_simplified(
            self.get_api_response(self.first_index)
        )
        self.assertIsInstance(li, list)
        self.assertEqual(len(li), self.entries_per_page)

    @requests_mock.Mocker()
    def test_model_map(self, http_mocker):
        """Check if all the keys of model are present in the model created by
           the `transport_response_simplified`

        """
        http_mocker.get(self.test_re, text=self.mock_response)
        fl = self.get_fl()
        li = fl.transport_response_simplified(self.get_api_response(self.first_index))
        di = li[0]
        self.assertIsInstance(di, dict)
        pubs = [k for k in vars(fl.MODEL).keys() if not k.startswith("_")]
        for k in pubs:
            if k not in ["last_seen", "task_id", "id"]:
                self.assertIn(k, di)

    @requests_mock.Mocker()
    def test_api_request(self, http_mocker):
        """Test API request for rate limit handling

        """
        http_mocker.get(self.test_re, text=self.mock_limit_twice_response)
        with patch.object(time, "sleep", wraps=time.sleep) as sleepmock:
            self.get_api_response(self.first_index)
            self.assertEqual(sleepmock.call_count, 2)

    @requests_mock.Mocker()
    def test_request_headers(self, http_mocker):
        fl = self.create_fl_with_db(http_mocker)
        fl.run()
        self.assertNotEqual(len(http_mocker.request_history), 0)
        for request in http_mocker.request_history:
            assert "User-Agent" in request.headers
            user_agent = request.headers["User-Agent"]
            assert "Software Heritage Lister" in user_agent
            assert swh.lister.__version__ in user_agent

    def scheduled_tasks_test(
        self, next_api_response_file, next_last_index, http_mocker
    ):
        """Check that no loading tasks get disabled when processing a new
        page of repositories returned by a forge API
        """
        fl = self.create_fl_with_db(http_mocker)

        # process first page of repositories listing
        fl.run()

        # process second page of repositories listing
        prev_last_index = self.last_index
        self.first_index = self.last_index
        self.last_index = next_last_index
        self.good_api_response_file = next_api_response_file
        fl.run(min_bound=prev_last_index)

        # check expected number of ingested repos and loading tasks
        ingested_repos = list(fl.db_query_range(0, self.last_index))
        self.assertEqual(len(ingested_repos), len(self.scheduler_tasks))
        self.assertEqual(len(ingested_repos), 2 * self.entries_per_page)

        # check tasks are not disabled
        for task in self.scheduler_tasks:
            self.assertTrue(task["status"] != "disabled")


class HttpSimpleListerTester(HttpListerTesterBase, abc.ABC):
    """Base testing class for subclass of
       :class:`swh.lister.core.simple)_lister.SimpleLister`

    See :class:`swh.lister.pypi.tests.test_lister` for an example of how
    to customize for a specific listing service.

    """

    entries = AbstractAttribute(
        "Number of results " "in good response"
    )  # type: Union[AbstractAttribute, int]
    PAGE = AbstractAttribute(
        "URL of the server api's unique page to retrieve and " "parse for information"
    )  # type: Union[AbstractAttribute, str]

    def get_fl(self, override_config=None):
        """Retrieve an instance of fake lister (fl).

        """
        if override_config or self.fl is None:
            self.fl = self.Lister(override_config=override_config)
            self.fl.INITIAL_BACKOFF = 1

        self.fl.reset_backoff()
        return self.fl

    def mock_response(self, request, context):
        self.fl.reset_backoff()
        self.rate_limit = 1
        context.status_code = 200
        custom_headers = self.response_headers(request)
        context.headers.update(custom_headers)
        response_file = self.good_api_response_file

        with open(
            "swh/lister/%s/tests/%s" % (self.lister_subdir, response_file),
            "r",
            encoding="utf-8",
        ) as r:
            return r.read()

    @requests_mock.Mocker()
    def test_api_request(self, http_mocker):
        """Test API request for rate limit handling

        """
        http_mocker.get(self.PAGE, text=self.mock_limit_twice_response)
        with patch.object(time, "sleep", wraps=time.sleep) as sleepmock:
            self.get_api_response(0)
            self.assertEqual(sleepmock.call_count, 2)

    @requests_mock.Mocker()
    def test_model_map(self, http_mocker):
        """Check if all the keys of model are present in the model created by
           the `transport_response_simplified`

        """
        http_mocker.get(self.PAGE, text=self.mock_response)
        fl = self.get_fl()
        li = fl.list_packages(self.get_api_response(0))
        li = fl.transport_response_simplified(li)
        di = li[0]
        self.assertIsInstance(di, dict)
        pubs = [k for k in vars(fl.MODEL).keys() if not k.startswith("_")]
        for k in pubs:
            if k not in ["last_seen", "task_id", "id"]:
                self.assertIn(k, di)

    @requests_mock.Mocker()
    def test_repos_list(self, http_mocker):
        """Test the number of packages listed by the lister

        """
        http_mocker.get(self.PAGE, text=self.mock_response)
        li = self.get_fl().list_packages(self.get_api_response(0))
        self.assertIsInstance(li, list)
        self.assertEqual(len(li), self.entries)
