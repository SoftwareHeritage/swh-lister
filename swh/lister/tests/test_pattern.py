# Copyright (C) 2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

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
        scheduler=swh_scheduler, url="https://example.com", instance="example.com",
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
