# Copyright (C) 2019 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from os.path import join, dirname
import re
from urllib.parse import urlparse
from unittest.mock import Mock

import requests_mock
from sqlalchemy import create_engine

from swh.lister.cgit.lister import CGitLister
from swh.lister.tests.test_utils import init_db


DATADIR = join(dirname(__file__), 'data')


def get_response_cb(request, context):
    url = urlparse(request.url)
    dirname = url.hostname
    filename = url.path[1:-1].replace('/', '_')
    if url.query:
        filename += ',' + url.query
    resp = open(join(DATADIR, dirname, filename), 'rb').read()
    return resp.decode('ascii', 'ignore')


def test_lister_no_page():
    with requests_mock.Mocker() as m:
        m.get(re.compile('http://git.savannah.gnu.org'), text=get_response_cb)
        lister = CGitLister()

        assert lister.url == 'http://git.savannah.gnu.org/cgit/'

        repos = list(lister.get_repos())
        assert len(repos) == 977

        assert repos[0] == 'http://git.savannah.gnu.org/cgit/elisp-es.git/'
        # note the url below is NOT a subpath of /cgit/
        assert repos[-1] == 'http://git.savannah.gnu.org/path/to/yetris.git/'  # noqa
        # note the url below is NOT on the same server
        assert repos[-2] == 'http://example.org/cgit/xstarcastle.git/'


def test_lister_model():
    with requests_mock.Mocker() as m:
        m.get(re.compile('http://git.savannah.gnu.org'), text=get_response_cb)
        lister = CGitLister()

        repo = next(lister.get_repos())

        model = lister.build_model(repo)
        assert model == {
            'uid': 'http://git.savannah.gnu.org/cgit/elisp-es.git/',
            'name': 'elisp-es.git',
            'origin_type': 'git',
            'instance': 'git.savannah.gnu.org',
            'origin_url': 'https://git.savannah.gnu.org/git/elisp-es.git'
            }


def test_lister_with_pages():
    with requests_mock.Mocker() as m:
        m.get(re.compile('http://git.tizen/cgit/'), text=get_response_cb)
        lister = CGitLister(url='http://git.tizen/cgit/')

        assert lister.url == 'http://git.tizen/cgit/'

        repos = list(lister.get_repos())
        # we should have 16 repos (listed on 3 pages)
        assert len(repos) == 16


def test_lister_run():
    with requests_mock.Mocker() as m:
        m.get(re.compile('http://git.tizen/cgit/'), text=get_response_cb)
        db = init_db()
        conf = {'lister': {'cls': 'local', 'args': {'db': db.url()}}}
        lister = CGitLister(url='http://git.tizen/cgit/',
                            override_config=conf)
        engine = create_engine(db.url())
        lister.MODEL.metadata.create_all(engine)
        lister.schedule_missing_tasks = Mock(return_value=None)
        lister.run()
