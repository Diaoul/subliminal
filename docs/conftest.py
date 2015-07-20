# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

import pytest
from vcr import VCR

vcr = VCR(path_transformer=lambda path: path + '.yaml',
          match_on=['method', 'scheme', 'host', 'port', 'path', 'query', 'body'],
          cassette_library_dir=os.path.join('docs', 'cassettes'))


@pytest.yield_fixture(autouse=True)
def auto_vcr(request, tmpdir, monkeypatch):
    monkeypatch.chdir(str(tmpdir))
    with vcr.use_cassette('test_' + request.fspath.purebasename):
        yield
