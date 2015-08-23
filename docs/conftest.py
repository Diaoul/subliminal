# -*- coding: utf-8 -*-
import os
import sys

import pytest
try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock
from vcr import VCR

from subliminal.cache import region

vcr = VCR(path_transformer=lambda path: path + '.yaml',
          match_on=['method', 'scheme', 'host', 'port', 'path', 'query', 'body'],
          cassette_library_dir=os.path.join('docs', 'cassettes'))


@pytest.fixture(autouse=True, scope='session')
def configure_region():
    region.configure('dogpile.cache.null')
    region.configure = Mock()


@pytest.fixture(autouse=True)
def chdir(tmpdir, monkeypatch):
    monkeypatch.chdir(str(tmpdir))


@pytest.yield_fixture(autouse=True)
def use_cassette(request):
    with vcr.use_cassette('test_' + request.fspath.purebasename):
        yield


@pytest.fixture(autouse=True)
def skip_python_2():
    if sys.version_info < (3, 0):
        return pytest.skip('Requires python 3')
