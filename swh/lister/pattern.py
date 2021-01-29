# Copyright (C) 2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from dataclasses import dataclass
from typing import Any, Dict, Generic, Iterable, Iterator, List, Optional, TypeVar

from swh.core.config import load_from_envvar
from swh.core.utils import grouper
from swh.scheduler import get_scheduler, model
from swh.scheduler.interface import SchedulerInterface


@dataclass
class ListerStats:
    pages: int = 0
    origins: int = 0

    def __add__(self, other: "ListerStats") -> "ListerStats":
        return self.__class__(self.pages + other.pages, self.origins + other.origins)

    def __iadd__(self, other: "ListerStats"):
        self.pages += other.pages
        self.origins += other.origins

    def dict(self) -> Dict[str, int]:
        return {"pages": self.pages, "origins": self.origins}


StateType = TypeVar("StateType")
PageType = TypeVar("PageType")

BackendStateType = Dict[str, Any]
CredentialsType = Optional[Dict[str, Dict[str, List[Dict[str, str]]]]]


class Lister(Generic[StateType, PageType]):
    """The base class for a Software Heritage lister.

    A lister scrapes a page by page list of origins from an upstream (a forge, the API
    of a package manager, ...), and massages the results of that scrape into a list of
    origins that are recorded by the scheduler backend.

    The main loop of the lister, :meth:`run`, basically revolves around the
    :meth:`get_pages` iterator, which sets up the lister state, then yields the scrape
    results page by page. The :meth:`get_origins_from_page` method converts the pages
    into a list of :class:`model.ListedOrigin`, sent to the scheduler at every page. The
    :meth:`commit_page` method can be used to update the lister state after a page of
    origins has been recorded in the scheduler backend.

    The :func:`finalize` method is called at lister teardown (whether the run has
    been successful or not) to update the local :attr:`state` object before it's sent to
    the database. This method must set the :attr:`updated` attribute if an updated
    state needs to be sent to the scheduler backend. This method can call
    :func:`get_state_from_scheduler` to refresh and merge the lister state from the
    scheduler before it's finalized (and potentially minimize the risk of race
    conditions between concurrent runs of the lister).

    The state of the lister is serialized and deserialized from the dict stored in the
    scheduler backend, using the :meth:`state_from_dict` and :meth:`state_to_dict`
    methods.

    Args:
      scheduler: the instance of the Scheduler being used to register the
        origins listed by this lister
      url: a URL representing this lister, e.g. the API's base URL
      instance: the instance name used, in conjunction with :attr:`LISTER_NAME`, to
        uniquely identify this lister instance.
      credentials: dictionary of credentials for all listers. The first level
        identifies the :attr:`LISTER_NAME`, the second level the lister
        :attr:`instance`. The final level is a list of dicts containing the
        expected credentials for the given instance of that lister.

    Generic types:
      - *StateType*: concrete lister type; should usually be a :class:`dataclass` for
        stricter typing
      - *PageType*: type of scrape results; can usually be a :class:`requests.Response`,
        or a :class:`dict`

    """

    LISTER_NAME: str = ""

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: str,
        instance: str,
        credentials: CredentialsType = None,
    ):
        if not self.LISTER_NAME:
            raise ValueError("Must set the LISTER_NAME attribute on Lister classes")

        self.url = url
        self.instance = instance

        self.scheduler = scheduler

        if not credentials:
            credentials = {}
        self.credentials = list(
            credentials.get(self.LISTER_NAME, {}).get(self.instance, [])
        )

        # store the initial state of the lister
        self.state = self.get_state_from_scheduler()
        self.updated = False

    def run(self) -> ListerStats:
        """Run the lister.

        Returns:
          A counter with the number of pages and origins seen for this run
          of the lister.

        """
        full_stats = ListerStats()

        try:
            for page in self.get_pages():
                full_stats.pages += 1
                origins = self.get_origins_from_page(page)
                full_stats.origins += self.send_origins(origins)
                self.commit_page(page)
        finally:
            self.finalize()
            if self.updated:
                self.set_state_in_scheduler()

        return full_stats

    def get_state_from_scheduler(self) -> StateType:
        """Update the state in the current instance from the state in the scheduler backend.

        This updates :attr:`lister_obj`, and returns its (deserialized) current state,
        to allow for comparison with the local state.

        Returns:
          the state retrieved from the scheduler backend
        """
        self.lister_obj = self.scheduler.get_or_create_lister(
            name=self.LISTER_NAME, instance_name=self.instance
        )
        return self.state_from_dict(self.lister_obj.current_state)

    def set_state_in_scheduler(self) -> None:
        """Update the state in the scheduler backend from the state of the current instance.

        Raises:
          :class:`swh.scheduler.exc.StaleData` in case of a race condition between
          concurrent listers (from :meth:`swh.scheduler.Scheduler.update_lister`).
        """
        self.lister_obj.current_state = self.state_to_dict(self.state)
        self.lister_obj = self.scheduler.update_lister(self.lister_obj)

    # State management to/from the scheduler

    def state_from_dict(self, d: BackendStateType) -> StateType:
        """Convert the state stored in the scheduler backend (as a dict),
        to the concrete StateType for this lister."""
        raise NotImplementedError

    def state_to_dict(self, state: StateType) -> BackendStateType:
        """Convert the StateType for this lister to its serialization as dict for
        storage in the scheduler.

        Values must be JSON-compatible as that's what the backend database expects.
        """
        raise NotImplementedError

    def finalize(self) -> None:
        """Custom hook to finalize the lister state before returning from the main loop.

        This method must set :attr:`updated` if the lister has done some work.

        If relevant, this method can use :meth`get_state_from_scheduler` to merge the
        current lister state with the one from the scheduler backend, reducing the risk
        of race conditions if we're running concurrent listings.

        This method is called in a `finally` block, which means it will also run when
        the lister fails.

        """
        pass

    # Actual listing logic

    def get_pages(self) -> Iterator[PageType]:
        """Retrieve a list of pages of listed results. This is the main loop of the lister.

        Returns:
          an iterator of raw pages fetched from the platform currently being listed.
        """
        raise NotImplementedError

    def get_origins_from_page(self, page: PageType) -> Iterator[model.ListedOrigin]:
        """Extract a list of :class:`model.ListedOrigin` from a raw page of results.

        Args:
          page: a single page of results
        Returns:
          an iterator for the origins present on the given page of results
        """
        raise NotImplementedError

    def commit_page(self, page: PageType) -> None:
        """Custom hook called after the current page has been committed in the scheduler
        backend.

        This method can be used to update the state after a page of origins has been
        successfully recorded in the scheduler backend. If the new state should be
        recorded at the point the lister completes, the :attr:`updated` attribute must
        be set.

        """
        pass

    def send_origins(self, origins: Iterable[model.ListedOrigin]) -> int:
        """Record a list of :class:`model.ListedOrigin` in the scheduler.

        Returns:
          the number of listed origins recorded in the scheduler
        """
        count = 0
        for batch_origins in grouper(origins, n=1000):
            ret = self.scheduler.record_listed_origins(batch_origins)
            count += len(ret)

        return count

    @classmethod
    def from_config(cls, scheduler: Dict[str, Any], **config: Any):
        """Instantiate a lister from a configuration dict.

        This is basically a backwards-compatibility shim for the CLI.

        Args:
          scheduler: instantiation config for the scheduler
          config: the configuration dict for the lister, with the following keys:
            - credentials (optional): credentials list for the scheduler
            - any other kwargs passed to the lister.

        Returns:
          the instantiated lister
        """
        # Drop the legacy config keys which aren't used for this generation of listers.
        for legacy_key in ("storage", "lister", "celery"):
            config.pop(legacy_key, None)

        # Instantiate the scheduler
        scheduler_instance = get_scheduler(**scheduler)

        return cls(scheduler=scheduler_instance, **config)

    @classmethod
    def from_configfile(cls, **kwargs: Any):
        """Instantiate a lister from the configuration loaded from the
        SWH_CONFIG_FILENAME envvar, with potential extra keyword arguments
        if their value is not None.

        Args:
            kwargs: kwargs passed to the lister instantiation
        """
        config = dict(load_from_envvar())
        config.update({k: v for k, v in kwargs.items() if v is not None})
        return cls.from_config(**config)


class StatelessLister(Lister[None, PageType], Generic[PageType]):
    def state_from_dict(self, d: BackendStateType) -> None:
        """Always return empty state"""
        return None

    def state_to_dict(self, state: None) -> BackendStateType:
        """Always set empty state"""
        return {}
