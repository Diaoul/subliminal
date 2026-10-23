"""Docs conftest.py."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest
from vcr import VCR

from subliminal.cache import region

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

vcr = VCR(
    path_transformer=lambda path: path + '.yaml',
    record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
    match_on=['method', 'scheme', 'host', 'port', 'path', 'query', 'body'],
    cassette_library_dir=os.path.realpath(os.path.join('docs', 'cassettes')),
)


@pytest.fixture(autouse=True, scope='session')
def _configure_region() -> None:
    region.configure('dogpile.cache.null')
    region.configure = Mock()


@pytest.fixture(autouse=True)
def _chdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)


@pytest.fixture(autouse=True)
def use_cassette(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """Use VCR cassette automatically."""
    with vcr.use_cassette('test_' + request.fspath.purebasename):  # ty: ignore[unresolved-attribute]
        yield
