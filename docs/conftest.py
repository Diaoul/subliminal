import os
import sys
from unittest.mock import Mock

import pytest
from vcr import VCR

from subliminal.cache import region

vcr = VCR(
    path_transformer=lambda path: path + '.yaml',
    record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
    match_on=['method', 'scheme', 'host', 'port', 'path', 'query', 'body'],
    cassette_library_dir=os.path.realpath(os.path.join('docs', 'cassettes')),
)


@pytest.fixture(autouse=True, scope='session')
def configure_region():
    region.configure('dogpile.cache.null')
    region.configure = Mock()


@pytest.fixture(autouse=True)
def chdir(tmpdir, monkeypatch):
    monkeypatch.chdir(str(tmpdir))


@pytest.fixture(autouse=True)
def use_cassette(request):
    with vcr.use_cassette('test_' + request.fspath.purebasename):
        yield
