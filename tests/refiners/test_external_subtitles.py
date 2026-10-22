from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest
from babelfish import Language  # type: ignore[import-untyped]
from tests.conftest import ensure

from subliminal.refiners.external_subtitles import search_external_subtitles

if TYPE_CHECKING:
    from pathlib import Path

    from subliminal.video import Episode, Movie

# Core test
pytestmark = pytest.mark.core


@pytest.mark.asyncio
async def test_search_external_subtitles(episodes: dict[str, Episode], tmp_path: Path) -> None:
    video_name = os.path.split(episodes['bbt_s07e05'].name)[1]
    video_root = os.path.splitext(video_name)[0]
    video_path = ensure(tmp_path / video_name)
    expected_subtitles = {
        video_name + '.srt': Language('und'),
        video_root + '.srt': Language('und'),
        video_root + '.en.srt': Language('eng'),
        video_name + '.fra.srt': Language('fra'),
        video_root + '.pt-BR.srt': Language('por', 'BR'),
        video_name + '.sr_cyrl.sub': Language('srp', script='Cyrl'),
        video_name + '.re.srt': Language('und'),
        video_name + '.something.srt': Language('und'),
    }
    ensure(tmp_path / (os.path.basename(episodes['got_s03e10'].name) + '.srt'))
    for path in expected_subtitles:
        ensure(tmp_path / path)
    subtitles = await search_external_subtitles(video_path)
    subtitle_languages = {subtitle.subtitle_id: subtitle.language for subtitle in subtitles}
    assert subtitle_languages == expected_subtitles


@pytest.mark.asyncio
async def test_search_external_subtitles_archive(movies: dict[str, Movie], tmp_path: Path) -> None:
    video_name = os.path.split(movies['interstellar'].name)[1]
    video_root = os.path.splitext(video_name)[0]
    video_path = ensure(tmp_path / video_name)
    expected_subtitles = {
        video_name + '.srt': Language('und'),
        video_root + '.srt': Language('und'),
        video_root + '.en.srt': Language('eng'),
        video_name + '.fra.srt': Language('fra'),
        video_root + '.pt-BR.srt': Language('por', 'BR'),
        video_name + '.sr_cyrl.sub': Language('srp', script='Cyrl'),
        video_name + '.something.srt': Language('und'),
    }
    ensure(tmp_path / (os.path.split(movies['interstellar'].name)[1] + '.srt'))
    for path in expected_subtitles:
        ensure(tmp_path / path)
    subtitles = await search_external_subtitles(video_path)
    subtitle_languages = {subtitle.subtitle_id: subtitle.language for subtitle in subtitles}
    assert subtitle_languages == expected_subtitles


@pytest.mark.asyncio
async def test_search_external_subtitles_no_directory(
    movies: dict[str, Movie],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    video_name = os.path.split(movies['man_of_steel'].name)[1]
    video_root = os.path.splitext(video_name)[0]
    ensure(tmp_path / video_name)
    monkeypatch.chdir(tmp_path)
    expected_subtitles = {video_name + '.srt': Language('und'), video_root + '.en.srt': Language('eng')}
    for path in expected_subtitles:
        ensure(tmp_path / path)
    subtitles = await search_external_subtitles(video_name)
    subtitle_languages = {subtitle.subtitle_id: subtitle.language for subtitle in subtitles}
    assert subtitle_languages == expected_subtitles


@pytest.mark.asyncio
async def test_search_external_subtitles_in_directory(episodes: dict[str, Episode], tmp_path: Path) -> None:
    video_name = episodes['marvels_agents_of_shield_s02e06'].name
    video_root = os.path.splitext(video_name)[0]
    ensure(tmp_path / 'tvshows' / video_name)
    subtitles_directory = ensure(tmp_path / 'subtitles', directory=True)
    expected_subtitles = {video_name + '.srt': Language('und'), video_root + '.en.srt': Language('eng')}
    ensure(tmp_path / 'tvshows' / (video_name + '.fr.srt'))
    for path in expected_subtitles:
        ensure(tmp_path / 'subtitles' / path)
    subtitles = await search_external_subtitles(video_name, directory=subtitles_directory)
    subtitle_languages = {subtitle.subtitle_id: subtitle.language for subtitle in subtitles}
    assert subtitle_languages == expected_subtitles
