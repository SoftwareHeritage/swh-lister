# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import functools
import json
from pathlib import Path
from urllib.parse import unquote, urlparse

from swh.lister.hackage.lister import HackageLister


def json_callback(request, context, datadir):
    """Callback for requests_mock that load a json file regarding a page number"""
    page = request.json()["page"]

    unquoted_url = unquote(request.url)
    url = urlparse(unquoted_url)
    dirname = "%s_%s" % (url.scheme, url.hostname)
    filename = url.path[1:]
    if filename.endswith("/"):
        filename = filename[:-1]
    filename = filename.replace("/", "_")

    return json.loads(Path(datadir, dirname, f"{filename}_{page}").read_text())


def test_hackage_lister(swh_scheduler, requests_mock, datadir):

    requests_mock.post(
        url="https://hackage.haskell.org/packages/search",
        status_code=200,
        json=functools.partial(json_callback, datadir=datadir),
    )

    expected_origins = []

    for page in [0, 1, 2]:
        data = json.loads(
            Path(
                datadir, "https_hackage.haskell.org", f"packages_search_{page}"
            ).read_text()
        )
        for entry in data["pageContents"]:
            pkgname = entry["name"]["display"]
            expected_origins.append(
                {"url": f"https://hackage.haskell.org/package/{pkgname}"}
            )

    lister = HackageLister(scheduler=swh_scheduler)
    res = lister.run()

    assert res.pages == 3
    assert res.origins == res.pages * 50

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    assert len(scheduler_origins) == len(expected_origins)

    assert {
        (
            scheduled.visit_type,
            scheduled.url,
        )
        for scheduled in scheduler_origins
    } == {
        (
            "hackage",
            expected["url"],
        )
        for expected in expected_origins
    }


def test_hackage_lister_pagination_49(swh_scheduler, requests_mock, datadir):
    requests_mock.post(
        url="https://fake49.haskell.org/packages/search",
        status_code=200,
        json=functools.partial(json_callback, datadir=datadir),
    )
    lister = HackageLister(scheduler=swh_scheduler, url="https://fake49.haskell.org/")
    pages = list(lister.get_pages())
    # there should be 1 page with 49 entries
    assert len(pages) == 1
    assert len(pages[0]) == 49


def test_hackage_lister_pagination_51(swh_scheduler, requests_mock, datadir):
    requests_mock.post(
        url="https://fake51.haskell.org/packages/search",
        status_code=200,
        json=functools.partial(json_callback, datadir=datadir),
    )
    lister = HackageLister(scheduler=swh_scheduler, url="https://fake51.haskell.org/")
    pages = list(lister.get_pages())
    # there should be 2 pages with 50 + 1 entries
    assert len(pages) == 2
    assert len(pages[0]) == 50
    assert len(pages[1]) == 1
