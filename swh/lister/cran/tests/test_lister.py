# Copyright (C) 2019-2023 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from os import path

import pandas
import pyreadr
import pytest

from swh.lister.cran.lister import CRAN_MIRROR_URL, CRANLister

CRAN_INFO_DB_DATA = {
    "/srv/ftp/pub/R/src/contrib/Archive/zooimage/zooimage_3.0-3.tar.gz": {
        "size": 2482446.0,
        "isdir": False,
        "mode": 436,
        "mtime": pandas.Timestamp("2013-02-11 20:03:00.351782400"),
        "ctime": pandas.Timestamp("2023-08-12 16:02:51.731749120"),
        "atime": pandas.Timestamp("2023-08-12 18:26:53.976175872"),
        "uid": 1001,
        "gid": 1001,
        "uname": "hornik",
        "grname": "cranadmin",
    },
    "/srv/ftp/pub/R/src/contrib/Archive/zooimage/zooimage_3.0-5.tar.gz": {
        "size": 2483495.0,
        "isdir": False,
        "mode": 436,
        "mtime": pandas.Timestamp("2014-03-02 12:20:17.842085376"),
        "ctime": pandas.Timestamp("2023-08-12 16:02:51.731749120"),
        "atime": pandas.Timestamp("2023-08-12 18:26:53.976175872"),
        "uid": 1008,
        "gid": 1001,
        "uname": "ripley",
        "grname": "cranadmin",
    },
    "/srv/ftp/pub/R/src/contrib/zooimage_5.5.2.tar.gz": {
        "size": 2980492.0,
        "isdir": False,
        "mode": 436,
        "mtime": pandas.Timestamp("2018-06-29 16:00:29.281795328"),
        "ctime": pandas.Timestamp("2023-08-12 16:02:52.227744768"),
        "atime": pandas.Timestamp("2023-08-12 18:13:24.175266560"),
        "uid": 1010,
        "gid": 1001,
        "uname": "ligges",
        "grname": "cranadmin",
    },
    "/srv/ftp/pub/R/src/contrib/Archive/xtune/xtune_0.1.0.tar.gz": {
        "size": 366098.0,
        "isdir": False,
        "mode": 436,
        "mtime": pandas.Timestamp("2019-05-24 09:00:04.697701120"),
        "ctime": pandas.Timestamp("2023-08-12 16:02:52.135745536"),
        "atime": pandas.Timestamp("2023-08-12 18:28:29.483338752"),
        "uid": 1010,
        "gid": 1001,
        "uname": "ligges",
        "grname": "cranadmin",
    },
    "/srv/ftp/pub/R/src/contrib/xtune_2.0.0.tar.gz": {
        "size": 4141076.0,
        "isdir": False,
        "mode": 436,
        "mtime": pandas.Timestamp("2023-06-18 22:40:04.242652416"),
        "ctime": pandas.Timestamp("2023-08-12 16:02:52.279744512"),
        "atime": pandas.Timestamp("2023-08-12 18:12:28.311755776"),
        "uid": 1010,
        "gid": 1001,
        "uname": "ligges",
        "grname": "cranadmin",
    },
    "/srv/ftp/pub/R/src/contrib/Old/0.50/bootstrap.tar.gz": {
        "size": 16306.0,
        "isdir": False,
        "mode": 436,
        "mtime": pandas.Timestamp("1997-04-16 10:10:36"),
        "ctime": pandas.Timestamp("2023-08-12 16:02:51.571750400"),
        "atime": pandas.Timestamp("2023-08-12 18:12:45.115608576"),
        "uid": 0,
        "gid": 1001,
        "uname": "root",
        "grname": "cranadmin",
    },
}


@pytest.fixture
def cran_info_db_rds_path(tmp_path):
    """Build a sample RDS file with small extract of CRAN database"""
    df = pandas.DataFrame.from_dict(
        CRAN_INFO_DB_DATA,
        orient="index",
    )
    rds_path = path.join(tmp_path, "cran_info_db.rds")
    pyreadr.write_rds(rds_path, df)
    return rds_path


def test_cran_lister_cran(swh_scheduler, mocker, cran_info_db_rds_path):
    lister = CRANLister(swh_scheduler)

    mock_download_file = mocker.patch("swh.lister.cran.lister.pyreadr.download_file")
    mock_download_file.return_value = cran_info_db_rds_path

    read_r = pyreadr.read_r

    def read_r_restore_data_lost_by_write_r(*args, **kwargs):
        result = read_r(*args, **kwargs)
        # DataFrame index is lost when calling pyreadr.write_rds so recreate
        # the same one as in original cran_info_db.rds file
        # https://github.com/ofajardo/pyreadr/issues/68
        result[None]["rownames"] = list(CRAN_INFO_DB_DATA.keys())
        result[None].set_index("rownames", inplace=True)
        # pyreadr.write_rds serializes datetime to string so restore datetime type
        # as in original cran_info_db.rds file
        for dt_column in ("mtime", "ctime", "atime"):
            result[None][dt_column] = pandas.to_datetime(
                result[None][dt_column], utc=True
            )
        return result

    mocker.patch(
        "swh.lister.cran.lister.pyreadr.read_r",
        wraps=read_r_restore_data_lost_by_write_r,
    )

    stats = lister.run()

    assert stats.pages == 1
    assert stats.origins == 2

    scheduler_origins = {
        o.url: o for o in swh_scheduler.get_listed_origins(lister.lister_obj.id).results
    }

    assert set(scheduler_origins.keys()) == {
        f"{CRAN_MIRROR_URL}/package=zooimage",
        f"{CRAN_MIRROR_URL}/package=xtune",
    }

    assert scheduler_origins[
        f"{CRAN_MIRROR_URL}/package=zooimage"
    ].extra_loader_arguments["artifacts"] == [
        {
            "url": f"{CRAN_MIRROR_URL}/src/contrib/Archive/zooimage/zooimage_3.0-3.tar.gz",  # noqa
            "package": "zooimage",
            "version": "3.0-3",
            "checksums": {"length": 2482446},
        },
        {
            "url": f"{CRAN_MIRROR_URL}/src/contrib/Archive/zooimage/zooimage_3.0-5.tar.gz",  # noqa
            "package": "zooimage",
            "version": "3.0-5",
            "checksums": {"length": 2483495},
        },
        {
            "url": f"{CRAN_MIRROR_URL}/src/contrib/zooimage_5.5.2.tar.gz",
            "package": "zooimage",
            "version": "5.5.2",
            "checksums": {"length": 2980492},
        },
    ]

    assert scheduler_origins[f"{CRAN_MIRROR_URL}/package=xtune"].extra_loader_arguments[
        "artifacts"
    ] == [
        {
            "url": f"{CRAN_MIRROR_URL}/src/contrib/Archive/xtune/xtune_0.1.0.tar.gz",
            "package": "xtune",
            "version": "0.1.0",
            "checksums": {"length": 366098},
        },
        {
            "url": f"{CRAN_MIRROR_URL}/src/contrib/xtune_2.0.0.tar.gz",
            "package": "xtune",
            "version": "2.0.0",
            "checksums": {"length": 4141076},
        },
    ]


@pytest.mark.parametrize(
    "credentials, expected_credentials",
    [
        (None, []),
        ({"key": "value"}, []),
        (
            {"cran": {"cran": [{"username": "user", "password": "pass"}]}},
            [{"username": "user", "password": "pass"}],
        ),
    ],
)
def test_lister_cran_instantiation_with_credentials(
    credentials, expected_credentials, swh_scheduler
):
    lister = CRANLister(swh_scheduler, credentials=credentials)

    # Credentials are allowed in constructor
    assert lister.credentials == expected_credentials


def test_lister_cran_from_configfile(swh_scheduler_config, mocker):
    load_from_envvar = mocker.patch("swh.lister.pattern.load_from_envvar")
    load_from_envvar.return_value = {
        "scheduler": {"cls": "local", **swh_scheduler_config},
        "credentials": {},
    }
    lister = CRANLister.from_configfile()
    assert lister.scheduler is not None
    assert lister.credentials is not None
