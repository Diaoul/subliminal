from __future__ import annotations

import inspect
import os
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock

import pytest
from babelfish import Language  # type: ignore[import-untyped]
from vcr import VCR  # type: ignore[import-untyped]

from subliminal.extensions import refiner_manager
from subliminal.provider_pool import refine

if TYPE_CHECKING:
    from subliminal.video import Episode, Movie

vcr = VCR(
    path_transformer=lambda path: path + '.yaml',
    record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
    decode_compressed_response=True,
    match_on=['method', 'scheme', 'host', 'port', 'path', 'query', 'body'],
    cassette_library_dir=os.path.realpath(os.path.join('tests', 'cassettes', 'refiners')),
)


@pytest.fixture
def _mock_refiners(monkeypatch: pytest.MonkeyPatch) -> None:
    for refiner in refiner_manager:
        if inspect.isclass(refiner.plugin):
            if inspect.iscoroutinefunction(refiner.plugin.initialize):  # type: ignore[attr-defined]
                monkeypatch.setattr(refiner.plugin, 'initialize', AsyncMock())
                monkeypatch.setattr(
                    refiner.plugin,
                    'refine',
                    AsyncMock(return_value={'external_ids': {'mock': refiner.name}}),
                )
                monkeypatch.setattr(refiner.plugin, 'terminate', AsyncMock())
            else:
                monkeypatch.setattr(refiner.plugin, 'initialize', Mock())
                monkeypatch.setattr(refiner.plugin, 'refine', Mock())
                monkeypatch.setattr(refiner.plugin, 'terminate', Mock())
        else:
            monkeypatch.setattr(refiner, 'plugin', Mock())


@pytest.mark.usefixtures('_mock_refiners')
def test_refine_movie(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    languages = {Language('eng')}

    refine({video}, languages=languages)

    # test refiners
    for name in ('hash', 'metadata', 'omdb', 'tmdb', 'external_subtitles'):
        plugin = refiner_manager[name].plugin
        if inspect.isclass(plugin):
            assert plugin.refine.called  # type: ignore[attr-defined]
        else:
            assert plugin.called  # type: ignore[attr-defined]

    # for name in ('tvdb'):
    #     assert not refiner_manager[name].plugin.refine.called  # type: ignore[attr-defined]


@pytest.mark.usefixtures('_mock_refiners')
def test_refine_episode(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    languages = {Language('eng')}

    refine({video}, languages=languages)

    # test refiners
    for name in ('hash', 'metadata', 'omdb', 'tmdb', 'external_subtitles', 'tvdb'):
        plugin = refiner_manager[name].plugin
        if inspect.isclass(plugin):
            assert plugin.refine.called  # type: ignore[attr-defined]
        else:
            assert plugin.called  # type: ignore[attr-defined]
