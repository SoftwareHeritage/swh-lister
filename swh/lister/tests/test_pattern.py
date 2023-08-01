# Copyright (C) 2020-2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from itertools import tee
from typing import TYPE_CHECKING, Any, Dict, Iterator, List

import pytest

from swh.lister import pattern
from swh.scheduler.model import ListedOrigin

StateType = Dict[str, str]
OriginType = Dict[str, str]
PageType = List[OriginType]


class InstantiableLister(pattern.Lister[StateType, PageType]):
    """A lister that can only be instantiated, not run."""

    LISTER_NAME = "test-pattern-lister"

    def state_from_dict(self, d: Dict[str, str]) -> StateType:
        return d


def test_instantiation_fail_to_instantiate(swh_scheduler):
    """Instantiation without proper url or instance will raise."""
    # While instantiating with either a url or instance is fine...
    InstantiableLister(scheduler=swh_scheduler, url="https://example.com")
    InstantiableLister(scheduler=swh_scheduler, instance="example.com")

    # ... Instantiating will fail when:
    # - no instance nor url parameters are provided to the constructor
    with pytest.raises(ValueError, match="'url' or 'instance"):
        InstantiableLister(
            scheduler=swh_scheduler,
        )

    # - an instance, which is not in a net location format, is provided
    with pytest.raises(ValueError, match="net location"):
        InstantiableLister(scheduler=swh_scheduler, instance="http://example.com")


def test_instantiation(swh_scheduler):
    lister = InstantiableLister(
        scheduler=swh_scheduler, url="https://example.com", instance="example.com"
    )

    # check the lister was registered in the scheduler backend
    stored_lister = swh_scheduler.get_or_create_lister(
        name="test-pattern-lister", instance_name="example.com"
    )
    assert stored_lister == lister.lister_obj

    with pytest.raises(NotImplementedError):
        lister.run()


def test_lister_instance_name(swh_scheduler):
    lister = InstantiableLister(
        scheduler=swh_scheduler, url="https://example.org", instance="example"
    )

    assert lister.instance == "example"

    lister = InstantiableLister(scheduler=swh_scheduler, url="https://example.org")

    assert lister.instance == "example.org"


def test_instantiation_from_configfile(swh_scheduler, mocker):
    mock_load_from_envvar = mocker.patch("swh.lister.pattern.load_from_envvar")
    mock_get_scheduler = mocker.patch("swh.lister.pattern.get_scheduler")
    mock_load_from_envvar.return_value = {
        "scheduler": {},
        "url": "foo",
        "instance": "bar",
    }
    mock_get_scheduler.return_value = swh_scheduler

    lister = InstantiableLister.from_configfile()
    assert lister.url == "foo"
    assert lister.instance == "bar"

    lister = InstantiableLister.from_configfile(url="bar", instance="foo")
    assert lister.url == "bar"
    assert lister.instance == "foo"

    lister = InstantiableLister.from_configfile(url=None, instance="foo")
    assert lister.url == "foo"
    assert lister.instance == "foo"


if TYPE_CHECKING:
    _Base = pattern.Lister[Any, PageType]
else:
    _Base = object


class ListerMixin(_Base):
    def get_pages(self) -> Iterator[PageType]:
        for pageno in range(2):
            yield [
                {"url": f"https://example.com/{pageno:02d}{i:03d}"} for i in range(10)
            ]

    def get_origins_from_page(self, page: PageType) -> Iterator[ListedOrigin]:
        assert self.lister_obj.id is not None
        for origin in page:
            yield ListedOrigin(
                lister_id=self.lister_obj.id, url=origin["url"], visit_type="git"
            )


def check_listed_origins(swh_scheduler, lister, stored_lister):
    """Check that the listed origins match the ones in the lister"""
    # Gather the origins that are supposed to be listed
    lister_urls = sorted(
        sum([[o["url"] for o in page] for page in lister.get_pages()], [])
    )

    # And check the state of origins in the scheduler
    ret = swh_scheduler.get_listed_origins()
    assert ret.next_page_token is None
    assert len(ret.results) == len(lister_urls)

    for origin, expected_url in zip(ret.results, lister_urls):
        assert origin.url == expected_url
        assert origin.lister_id == stored_lister.id


class RunnableLister(ListerMixin, InstantiableLister):
    """A lister that can be run."""

    def state_to_dict(self, state: StateType) -> Dict[str, str]:
        return state

    def finalize(self) -> None:
        self.state["updated"] = "yes"
        self.updated = True


def test_run(swh_scheduler):
    lister = RunnableLister(
        scheduler=swh_scheduler, url="https://example.com", instance="example.com"
    )

    assert "updated" not in lister.state

    update_date = lister.lister_obj.updated

    run_result = lister.run()

    assert run_result.pages == 2
    assert run_result.origins == 20

    stored_lister = swh_scheduler.get_or_create_lister(
        name="test-pattern-lister", instance_name="example.com"
    )

    # Check that the finalize operation happened
    assert stored_lister.updated > update_date
    assert stored_lister.current_state["updated"] == "yes"

    check_listed_origins(swh_scheduler, lister, stored_lister)


class InstantiableStatelessLister(pattern.StatelessLister[PageType]):
    LISTER_NAME = "test-stateless-lister"


def test_stateless_instantiation(swh_scheduler):
    lister = InstantiableStatelessLister(
        scheduler=swh_scheduler,
        url="https://example.com",
        instance="example.com",
    )

    # check the lister was registered in the scheduler backend
    stored_lister = swh_scheduler.get_or_create_lister(
        name="test-stateless-lister", instance_name="example.com"
    )
    assert stored_lister == lister.lister_obj
    assert stored_lister.current_state == {}
    assert lister.state is None

    with pytest.raises(NotImplementedError):
        lister.run()


class RunnableStatelessLister(ListerMixin, InstantiableStatelessLister):
    def finalize(self):
        self.updated = True


def test_stateless_run(swh_scheduler):
    lister = RunnableStatelessLister(
        scheduler=swh_scheduler, url="https://example.com", instance="example.com"
    )

    update_date = lister.lister_obj.updated

    run_result = lister.run()

    assert run_result.pages == 2
    assert run_result.origins == 20

    stored_lister = swh_scheduler.get_or_create_lister(
        name="test-stateless-lister", instance_name="example.com"
    )

    # Check that the finalize operation happened
    assert stored_lister.updated > update_date
    assert stored_lister.current_state == {}

    # And that all origins are stored
    check_listed_origins(swh_scheduler, lister, stored_lister)


class ListerWithSameOriginInMultiplePages(RunnableStatelessLister):
    def get_pages(self) -> Iterator[PageType]:
        for _ in range(2):
            yield [{"url": "https://example.org/user/project"}]


def test_listed_origins_count(swh_scheduler):
    lister = ListerWithSameOriginInMultiplePages(
        scheduler=swh_scheduler, url="https://example.org", instance="example.org"
    )

    run_result = lister.run()

    assert run_result.pages == 2
    assert run_result.origins == 1


class ListerWithALotOfPagesWithALotOfOrigins(RunnableStatelessLister):
    def get_pages(self) -> Iterator[PageType]:
        for page in range(10):
            yield [
                {"url": f"https://example.org/page{page}/origin{origin}"}
                for origin in range(10)
            ]


@pytest.mark.parametrize(
    "max_pages,expected_pages",
    [
        (2, 2),
        (10, 10),
        (100, 10),
        # The default returns all 10 pages
        (None, 10),
    ],
)
def test_lister_max_pages(swh_scheduler, max_pages, expected_pages):
    extra_kwargs = {}
    if max_pages is not None:
        extra_kwargs["max_pages"] = max_pages

    lister = ListerWithALotOfPagesWithALotOfOrigins(
        scheduler=swh_scheduler,
        url="https://example.org",
        instance="example.org",
        **extra_kwargs,
    )

    run_result = lister.run()

    assert run_result.pages == expected_pages
    assert run_result.origins == expected_pages * 10


@pytest.mark.parametrize(
    "max_origins_per_page,expected_origins_per_page",
    [
        (2, 2),
        (10, 10),
        (100, 10),
        # The default returns all 10 origins per page
        (None, 10),
    ],
)
def test_lister_max_origins_per_page(
    swh_scheduler, max_origins_per_page, expected_origins_per_page
):
    extra_kwargs = {}
    if max_origins_per_page is not None:
        extra_kwargs["max_origins_per_page"] = max_origins_per_page

    lister = ListerWithALotOfPagesWithALotOfOrigins(
        scheduler=swh_scheduler,
        url="https://example.org",
        instance="example.org",
        **extra_kwargs,
    )

    run_result = lister.run()

    assert run_result.pages == 10
    assert run_result.origins == 10 * expected_origins_per_page


@pytest.mark.parametrize(
    "enable_origins,expected",
    [
        (True, True),
        (False, False),
        # default behavior is to enable all listed origins
        (None, True),
    ],
)
def test_lister_enable_origins(swh_scheduler, enable_origins, expected):
    extra_kwargs = {}
    if enable_origins is not None:
        extra_kwargs["enable_origins"] = enable_origins

    lister = ListerWithALotOfPagesWithALotOfOrigins(
        scheduler=swh_scheduler,
        url="https://example.org",
        instance="example.org",
        **extra_kwargs,
    )

    run_result = lister.run()
    assert run_result.pages == 10
    assert run_result.origins == 100

    origins = swh_scheduler.get_listed_origins(
        lister_id=lister.lister_obj.id, enabled=None
    ).results

    assert origins

    assert all(origin.enabled == expected for origin in origins)


@pytest.mark.parametrize("batch_size", [5, 10, 20])
def test_lister_send_origins_with_stream_is_flushed_regularly(
    swh_scheduler, mocker, batch_size
):
    """Ensure the send_origins method is flushing regularly records to the scheduler"""
    lister = RunnableLister(
        scheduler=swh_scheduler,
        url="https://example.com",
        instance="example.com",
        record_batch_size=batch_size,
    )

    def iterate_origins(lister: pattern.Lister) -> Iterator[ListedOrigin]:
        """Basic origin iteration to ease testing."""
        for page in lister.get_pages():
            for origin in lister.get_origins_from_page(page):
                yield origin

    all_origins, iterator_origins = tee(iterate_origins(lister))

    spy = mocker.spy(lister, "scheduler")
    lister.send_origins(iterator_origins)

    expected_nb_origins = len(list(all_origins))

    assert len(spy.method_calls) == expected_nb_origins / batch_size
