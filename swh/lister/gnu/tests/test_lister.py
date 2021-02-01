# Copyright (C) 2019-2021 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from ..lister import GNULister


def test_gnu_lister(swh_scheduler, requests_mock_datadir):
    lister = GNULister(scheduler=swh_scheduler)

    stats = lister.run()

    assert stats.pages == 1
    assert stats.origins == 383

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    assert len(scheduler_origins) == stats.origins

    for origin in scheduler_origins:
        assert origin.url.startswith(GNULister.GNU_FTP_URL)
        assert origin.last_update is not None
        assert "artifacts" in origin.extra_loader_arguments
        assert len(origin.extra_loader_arguments["artifacts"]) > 0


def test_gnu_lister_from_configfile(swh_scheduler_config, mocker):
    load_from_envvar = mocker.patch("swh.lister.pattern.load_from_envvar")
    load_from_envvar.return_value = {
        "scheduler": {"cls": "local", **swh_scheduler_config},
        "credentials": {},
    }
    lister = GNULister.from_configfile()
    assert lister.scheduler is not None
    assert lister.credentials is not None
