# Copyright (C) 2015-2020 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import abc
import datetime
import gzip
import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Type, Union

from requests import Response
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from swh.core import config
from swh.core.utils import grouper
from swh.scheduler import get_scheduler, utils

from .abstractattribute import AbstractAttribute

logger = logging.getLogger(__name__)


def utcnow():
    return datetime.datetime.now(tz=datetime.timezone.utc)


class FetchError(RuntimeError):
    def __init__(self, response):
        self.response = response

    def __str__(self):
        return repr(self.response)


DEFAULT_CONFIG = {
    "scheduler": {"cls": "memory"},
    "lister": {"cls": "local", "args": {"db": "postgresql:///lister",},},
    "credentials": {},
    "cache_responses": False,
}


class ListerBase(abc.ABC):
    """Lister core base class.
        Generally a source code hosting service provides an API endpoint
        for listing the set of stored repositories. A Lister is the discovery
        service responsible for finding this list, all at once or sequentially
        by parts, and queueing local tasks to fetch and ingest the referenced
        repositories.

        The core method in this class is ingest_data. Any subclasses should be
        calling this method one or more times to fetch and ingest data from API
        endpoints. See swh.lister.core.lister_base.IndexingLister for
        example usage.

        This class cannot be instantiated. Any instantiable Lister descending
        from ListerBase must provide at least the required overrides.
        (see member docstrings for details):

        Required Overrides:
            MODEL
            def transport_request
            def transport_response_to_string
            def transport_response_simplified
            def transport_quota_check

        Optional Overrides:
            def filter_before_inject
            def is_within_bounds
    """

    MODEL = AbstractAttribute(
        "Subclass type (not instance) of swh.lister.core.models.ModelBase "
        "customized for a specific service."
    )  # type: Union[AbstractAttribute, Type[Any]]
    LISTER_NAME = AbstractAttribute(
        "Lister's name"
    )  # type: Union[AbstractAttribute, str]

    def transport_request(self, identifier):
        """Given a target endpoint identifier to query, try once to request it.

        Implementation of this method determines the network request protocol.

        Args:
            identifier (string): unique identifier for an endpoint query.
                e.g. If the service indexes lists of repositories by date and
                time of creation, this might be that as a formatted string. Or
                it might be an integer UID. Or it might be nothing.
                It depends on what the service needs.
        Returns:
            the entire request response
        Raises:
            Will catch internal transport-dependent connection exceptions and
            raise swh.lister.core.lister_base.FetchError instead. Other
            non-connection exceptions should propagate unchanged.
        """
        pass

    def transport_response_to_string(self, response):
        """Convert the server response into a formatted string for logging.

        Implementation of this method depends on the shape of the network
        response object returned by the transport_request method.

        Args:
            response: the server response
        Returns:
            a pretty string of the response
        """
        pass

    def transport_response_simplified(self, response):
        """Convert the server response into list of a dict for each repo in the
            response, mapping columns in the lister's MODEL class to repo data.

        Implementation of this method depends on the server API spec and the
        shape of the network response object returned by the transport_request
        method.

        Args:
            response: response object from the server.
        Returns:
            list of repo MODEL dicts
             ( eg. [{'uid': r['id'], etc.} for r in response.json()] )
        """
        pass

    def transport_quota_check(self, response):
        """Check server response to see if we're hitting request rate limits.

        Implementation of this method depends on the server communication
        protocol and API spec and the shape of the network response object
        returned by the transport_request method.

        Args:
            response (session response): complete API query response
        Returns:
            1) must retry request? True/False
            2) seconds to delay if True
        """
        pass

    def filter_before_inject(self, models_list: List[Dict]) -> List[Dict]:
        """Filter models_list entries prior to injection in the db.
        This is ran directly after `transport_response_simplified`.

        Default implementation is to have no filtering.

        Args:
            models_list: list of dicts returned by
                         transport_response_simplified.
        Returns:
            models_list with entries changed according to custom logic.

        """
        return models_list

    def do_additional_checks(self, models_list: List[Dict]) -> List[Dict]:
        """Execute some additional checks on the model list (after the
        filtering).

        Default implementation is to run no check at all and to return
        the input as is.

        Args:
            models_list: list of dicts returned by
                         transport_response_simplified.

        Returns:
            models_list with entries if checks ok, False otherwise

        """
        return models_list

    def is_within_bounds(
        self, inner: int, lower: Optional[int] = None, upper: Optional[int] = None
    ) -> bool:
        """See if a sortable value is inside the range [lower,upper].

        MAY BE OVERRIDDEN, for example if the server indexable* key is
        technically sortable but not automatically so.

        * - ( see: swh.lister.core.indexing_lister.IndexingLister )

        Args:
            inner (sortable type): the value being checked
            lower (sortable type): optional lower bound
            upper (sortable type): optional upper bound
        Returns:
            whether inner is confined by the optional lower and upper bounds
        """
        try:
            if lower is None and upper is None:
                return True
            elif lower is None:
                ret = inner <= upper  # type: ignore
            elif upper is None:
                ret = inner >= lower
            else:
                ret = lower <= inner <= upper

            self.string_pattern_check(inner, lower, upper)
        except Exception as e:
            logger.error(
                str(e)
                + ": %s, %s, %s"
                % (
                    ("inner=%s%s" % (type(inner), inner)),
                    ("lower=%s%s" % (type(lower), lower)),
                    ("upper=%s%s" % (type(upper), upper)),
                )
            )
            raise

        return ret

    # You probably don't need to override anything below this line.

    INITIAL_BACKOFF = 10
    MAX_RETRIES = 7
    CONN_SLEEP = 10

    def __init__(self, override_config=None):
        self.backoff = self.INITIAL_BACKOFF
        self.config = config.load_from_envvar(DEFAULT_CONFIG)
        if self.config["cache_responses"]:
            cache_dir = self.config.get(
                "cache_dir", f"~/.cache/swh/lister/{self.LISTER_NAME}"
            )
            self.config["cache_dir"] = os.path.expanduser(cache_dir)
            config.prepare_folders(self.config, "cache_dir")

        if override_config:
            self.config.update(override_config)

        logger.debug("%s CONFIG=%s" % (self, self.config))
        self.scheduler = get_scheduler(**self.config["scheduler"])
        self.db_engine = create_engine(self.config["lister"]["args"]["db"])
        self.mk_session = sessionmaker(bind=self.db_engine)
        self.db_session = self.mk_session()

    def reset_backoff(self):
        """Reset exponential backoff timeout to initial level."""
        self.backoff = self.INITIAL_BACKOFF

    def back_off(self) -> int:
        """Get next exponential backoff timeout."""
        ret = self.backoff
        self.backoff *= 10
        return ret

    def safely_issue_request(self, identifier: int) -> Optional[Response]:
        """Make network request with retries, rate quotas, and response logs.

        Protocol is handled by the implementation of the transport_request
        method.

        Args:
            identifier: resource identifier
        Returns:
            server response
        """
        retries_left = self.MAX_RETRIES
        do_cache = self.config["cache_responses"]
        r = None
        while retries_left > 0:
            try:
                r = self.transport_request(identifier)
            except FetchError:
                # network-level connection error, try again
                logger.warning(
                    "connection error on %s: sleep for %d seconds"
                    % (identifier, self.CONN_SLEEP)
                )
                time.sleep(self.CONN_SLEEP)
                retries_left -= 1
                continue

            if do_cache:
                self.save_response(r)

            # detect throttling
            must_retry, delay = self.transport_quota_check(r)
            if must_retry:
                logger.warning(
                    "rate limited on %s: sleep for %f seconds" % (identifier, delay)
                )
                time.sleep(delay)
            else:  # request ok
                break

            retries_left -= 1

        if not retries_left:
            logger.warning("giving up on %s: max retries exceeded" % identifier)

        return r

    def db_query_equal(self, key: Any, value: Any):
        """Look in the db for a row with key == value

        Args:
            key: column key to look at
            value: value to look for in that column
        Returns:
            sqlalchemy.ext.declarative.declarative_base object
                with the given key == value
        """
        if isinstance(key, str):
            key = self.MODEL.__dict__[key]
        return self.db_session.query(self.MODEL).filter(key == value).first()

    def winnow_models(self, mlist, key, to_remove):
        """Given a list of models, remove any with <key> matching
            some member of a list of values.

        Args:
            mlist (list of model rows): the initial list of models
            key (column): the column to filter on
            to_remove (list): if anything in mlist has column <key> equal to
                one of the values in to_remove, it will be removed from the
                result
        Returns:
            A list of model rows starting from mlist minus any matching rows
        """
        if isinstance(key, str):
            key = self.MODEL.__dict__[key]

        if to_remove:
            return mlist.filter(~key.in_(to_remove)).all()
        else:
            return mlist.all()

    def db_num_entries(self):
        """Return the known number of entries in the lister db"""
        return self.db_session.query(func.count("*")).select_from(self.MODEL).scalar()

    def db_inject_repo(self, model_dict):
        """Add/update a new repo to the db and mark it last_seen now.

        Args:
            model_dict: dictionary mapping model keys to values

        Returns:
            new or updated sqlalchemy.ext.declarative.declarative_base
            object associated with the injection

        """
        sql_repo = self.db_query_equal("uid", model_dict["uid"])

        if not sql_repo:
            sql_repo = self.MODEL(**model_dict)
            self.db_session.add(sql_repo)
        else:
            for k in model_dict:
                setattr(sql_repo, k, model_dict[k])
            sql_repo.last_seen = utcnow()

        return sql_repo

    def task_dict(self, origin_type: str, origin_url: str, **kwargs) -> Dict[str, Any]:
        """Return special dict format for the tasks list

        Args:
            origin_type (string)
            origin_url (string)
        Returns:
            the same information in a different form
        """
        logger.debug("origin-url: %s, type: %s", origin_url, origin_type)
        _type = "load-%s" % origin_type
        _policy = kwargs.get("policy", "recurring")
        priority = kwargs.get("priority")
        kw = {"priority": priority} if priority else {}
        return utils.create_task_dict(_type, _policy, url=origin_url, **kw)

    def string_pattern_check(self, a, b, c=None):
        """When comparing indexable types in is_within_bounds, complex strings
            may not be allowed to differ in basic structure. If they do, it
            could be a sign of not understanding the data well. For instance,
            an ISO 8601 time string cannot be compared against its urlencoded
            equivalent, but this is an easy mistake to accidentally make. This
            method acts as a friendly sanity check.

        Args:
            a (string): inner component of the is_within_bounds method
            b (string): lower component of the is_within_bounds method
            c (string): upper component of the is_within_bounds method
        Returns:
            nothing
        Raises:
            TypeError if strings a, b, and c don't conform to the same basic
            pattern.
        """
        if isinstance(a, str):
            a_pattern = re.sub("[a-zA-Z0-9]", "[a-zA-Z0-9]", re.escape(a))
            if (
                isinstance(b, str)
                and (re.match(a_pattern, b) is None)
                or isinstance(c, str)
                and (re.match(a_pattern, c) is None)
            ):
                logger.debug(a_pattern)
                raise TypeError("incomparable string patterns detected")

    def inject_repo_data_into_db(self, models_list: List[Dict]) -> Dict:
        """Inject data into the db.

        Args:
            models_list: list of dicts mapping keys from the db model
                        for each repo to be injected
        Returns:
            dict of uid:sql_repo pairs

        """
        injected_repos = {}
        for m in models_list:
            injected_repos[m["uid"]] = self.db_inject_repo(m)
        return injected_repos

    def schedule_missing_tasks(
        self, models_list: List[Dict], injected_repos: Dict
    ) -> None:
        """Schedule any newly created db entries that do not have been
           scheduled yet.

        Args:
            models_list: List of dicts mapping keys in the db model
                         for each repo
            injected_repos: Dict of uid:sql_repo pairs that have just
                            been created

        Returns:
            Nothing. (Note that it Modifies injected_repos to set the new
            task_id).

        """
        tasks = {}

        def _task_key(m):
            return "%s-%s" % (m["type"], json.dumps(m["arguments"], sort_keys=True))

        for m in models_list:
            ir = injected_repos[m["uid"]]
            if not ir.task_id:
                # Patching the model instance to add the policy/priority task
                # scheduling
                if "policy" in self.config:
                    m["policy"] = self.config["policy"]
                if "priority" in self.config:
                    m["priority"] = self.config["priority"]
                task_dict = self.task_dict(**m)
                task_dict.setdefault("retries_left", 3)
                tasks[_task_key(task_dict)] = (ir, m, task_dict)

        gen_tasks = (task_dicts for (_, _, task_dicts) in tasks.values())
        for grouped_tasks in grouper(gen_tasks, n=1000):
            new_tasks = self.scheduler.create_tasks(list(grouped_tasks))
            for task in new_tasks:
                ir, m, _ = tasks[_task_key(task)]
                ir.task_id = task["id"]

    def ingest_data(self, identifier: int, checks: bool = False):
        """The core data fetch sequence. Request server endpoint. Simplify and
            filter response list of repositories. Inject repo information into
            local db. Queue loader tasks for linked repositories.

        Args:
            identifier: Resource identifier.
            checks (bool): Additional checks required
        """
        # Request (partial?) list of repositories info
        response = self.safely_issue_request(identifier)
        if not response:
            return response, []
        models_list = self.transport_response_simplified(response)
        models_list = self.filter_before_inject(models_list)
        if checks:
            models_list = self.do_additional_checks(models_list)
            if not models_list:
                return response, []
        # inject into local db
        injected = self.inject_repo_data_into_db(models_list)
        # queue workers
        self.schedule_missing_tasks(models_list, injected)
        return response, injected

    def save_response(self, response):
        """Log the response from a server request to a cache dir.

        Args:
            response: full server response
            cache_dir: system path for cache dir
        Returns:
            nothing
        """
        datepath = utcnow().isoformat()

        fname = os.path.join(self.config["cache_dir"], datepath + ".gz",)

        with gzip.open(fname, "w") as f:
            f.write(bytes(self.transport_response_to_string(response), "UTF-8"))
