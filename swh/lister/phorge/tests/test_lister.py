# Copyright (C) 2019-2026  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import functools

from swh.core.pytest_plugin import get_response_cb
from swh.lister import USER_AGENT_TEMPLATE
from swh.lister.phorge.lister import PhorgeLister

INSTANCE = "we.phorge.it"
URL = f"https://{INSTANCE}"
API_TOKEN = "foo"


def test_lister(
    swh_scheduler,
    requests_mock,
    datadir,
):

    lister = PhorgeLister(
        scheduler=swh_scheduler, url=URL, instance=INSTANCE, api_token=API_TOKEN
    )

    def match_request(request):
        return (
            request.headers.get("User-Agent")
            == USER_AGENT_TEMPLATE % PhorgeLister.LISTER_NAME
            and f"api.token={API_TOKEN}" in request.body
        )

    requests_mock.post(
        url=f"{URL}{lister.API_REPOSITORY_PATH}",
        status_code=200,
        body=functools.partial(get_response_cb, datadir=datadir),
        additional_matcher=match_request,
    )
    stats = lister.run()

    expected_nb_origins = 18

    assert stats.pages == 1
    assert stats.origins == expected_nb_origins

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    assert len(scheduler_origins) == expected_nb_origins
