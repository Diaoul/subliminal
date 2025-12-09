# ruff: noqa: PT011
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

from subliminal.utils import sanitize, timestamp
from subliminal.video import Episode, Movie, Video

if TYPE_CHECKING:
    from pathlib import Path

# Core test
pytestmark = pytest.mark.core


def test_video_exists_age_no_use_ctime(
    movies: dict[str, Movie],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    video = movies['man_of_steel']
    original_use_ctime = video.use_ctime
    video.use_ctime = False
    video_path = tmp_path / video.name
    video_path.parent.mkdir(parents=True)
    video_path.touch()
    ts = timestamp(datetime.now(timezone.utc) - timedelta(days=3))
    os.utime(video_path, (ts, ts))
    assert video.exists
    assert timedelta(days=3) <= video.age < timedelta(days=3, seconds=1)
    # Reset
    video.use_ctime = original_use_ctime


def test_video_exists_age(movies: dict[str, Movie], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    try:
        from win32_setctime import SUPPORTED, setctime
    except (ImportError, ModuleNotFoundError):
        SUPPORTED = False
        setctime = None

    monkeypatch.chdir(tmp_path)
    video = movies['man_of_steel']
    video_path = tmp_path / video.name
    video_path.parent.mkdir(parents=True)
    video_path.touch()
    ts = timestamp(datetime.now(timezone.utc) - timedelta(days=3))
    if SUPPORTED:
        # Modify ctime on Windows
        setctime(video_path, ts)
    os.utime(video_path, (ts, ts))
    assert video.exists
    assert timedelta(days=3) <= video.age < timedelta(days=3, seconds=1)


def test_video_age(movies: dict[str, Movie], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert movies['man_of_steel'].age == timedelta()


def test_video_fromguess_episode(episodes: dict[str, Episode], monkeypatch: pytest.MonkeyPatch) -> None:
    guess = {'type': 'episode'}
    monkeypatch.setattr(Episode, 'fromguess', Mock())
    Video.fromguess(episodes['bbt_s07e05'].name, guess)
    assert Episode.fromguess.called  # type: ignore[attr-defined]


def test_video_fromguess_movie(movies: dict[str, Movie], monkeypatch: pytest.MonkeyPatch) -> None:
    guess = {'type': 'movie'}
    monkeypatch.setattr(Movie, 'fromguess', Mock())
    Video.fromguess(movies['man_of_steel'].name, guess)
    assert Movie.fromguess.called  # type: ignore[attr-defined]


def test_video_fromguess_wrong_type(episodes: dict[str, Episode]) -> None:
    guess = {'type': 'subtitle'}
    with pytest.raises(ValueError) as excinfo:
        Video.fromguess(episodes['bbt_s07e05'].name, guess)
    assert str(excinfo.value) == 'The guess must be an episode or a movie guess'


def test_video_fromname_movie(movies: dict[str, Movie]) -> None:
    video = Video.fromname(movies['man_of_steel'].name)
    assert isinstance(video, Movie)
    assert video.name == movies['man_of_steel'].name
    assert video.source == movies['man_of_steel'].source
    assert video.release_group == movies['man_of_steel'].release_group
    assert video.resolution == movies['man_of_steel'].resolution
    assert video.video_codec == movies['man_of_steel'].video_codec
    assert video.audio_codec is None
    assert video.imdb_id is None
    assert video.hashes == {}
    assert video.size is None
    assert video.subtitle_languages == set()
    assert video.title == movies['man_of_steel'].title
    assert video.year == movies['man_of_steel'].year


def test_video_fromname_episode(episodes: dict[str, Episode]) -> None:
    video = Video.fromname(episodes['bbt_s07e05'].name)
    assert isinstance(video, Episode)
    assert video.name == episodes['bbt_s07e05'].name
    assert video.source == episodes['bbt_s07e05'].source
    assert video.release_group == episodes['bbt_s07e05'].release_group
    assert video.resolution == episodes['bbt_s07e05'].resolution
    assert video.video_codec == episodes['bbt_s07e05'].video_codec
    assert video.audio_codec is None
    assert video.imdb_id is None
    assert video.hashes == {}
    assert video.size is None
    assert video.subtitle_languages == set()
    assert video.series == episodes['bbt_s07e05'].series
    assert video.season == episodes['bbt_s07e05'].season
    assert video.episode == episodes['bbt_s07e05'].episode
    assert video.title is None
    assert video.year is None
    assert video.tvdb_id is None


def test_video_fromname_episode_no_season(episodes: dict[str, Episode]) -> None:
    video = Video.fromname(episodes['the_jinx_e05'].name)
    assert isinstance(video, Episode)
    assert video.name == episodes['the_jinx_e05'].name
    assert video.source == episodes['the_jinx_e05'].source
    assert video.release_group == episodes['the_jinx_e05'].release_group
    assert video.resolution == episodes['the_jinx_e05'].resolution
    assert video.video_codec == episodes['the_jinx_e05'].video_codec
    assert video.audio_codec is None
    assert video.imdb_id is None
    assert video.hashes == {}
    assert video.size is None
    assert video.subtitle_languages == set()
    assert sanitize(video.series) == sanitize(episodes['the_jinx_e05'].series)
    assert video.season == episodes['the_jinx_e05'].season
    assert video.episode == episodes['the_jinx_e05'].episode
    assert video.title is None
    assert video.year is None
    assert video.tvdb_id is None


def test_video_hash(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    assert hash(video) == hash(video.name)


def test_movie_matches(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    assert video.matches('Man of Steel')


def test_episode_matches(episodes: dict[str, Episode]) -> None:
    video = episodes['marvels_jessica_jones_s01e13']
    assert video.matches('Jessica Jones')
    assert video.matches("Marvel's Jessica Jones")


def test_movie_repr(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    assert isinstance(f'{video!r}', str)


def test_episode_repr(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    assert isinstance(f'{video!r}', str)


def test_episode_from_guess_multi_episode(episodes: dict[str, Episode]) -> None:
    video = Video.fromname(episodes['Marvels.Agents.of.S.H.I.E.L.D.S05E01-E02'].name)
    # Multi-ep is converted to single-ep by taking the lowest episode number
    assert isinstance(video, Episode)
    assert video.episode == episodes['Marvels.Agents.of.S.H.I.E.L.D.S05E01-E02'].episode


def test_episode_fromguess_wrong_type(episodes: dict[str, Episode]) -> None:
    guess = {'type': 'subtitle'}
    with pytest.raises(ValueError, match='The guess must be an episode guess'):
        Episode.fromguess(episodes['bbt_s07e05'].name, guess)


def test_episode_fromguess_insufficient_data(episodes: dict[str, Episode]) -> None:
    guess = {'type': 'episode'}
    with pytest.raises(ValueError, match='Insufficient data to process the guess'):
        Episode.fromguess(episodes['bbt_s07e05'].name, guess)


def test_movie_fromguess_wrong_type(movies: dict[str, Movie]) -> None:
    guess = {'type': 'subtitle'}
    with pytest.raises(ValueError, match='The guess must be a movie guess'):
        Movie.fromguess(movies['man_of_steel'].name, guess)


def test_movie_fromguess_insufficient_data(movies: dict[str, Movie]) -> None:
    guess = {'type': 'movie'}
    with pytest.raises(ValueError, match='Insufficient data to process the guess'):
        Movie.fromguess(movies['man_of_steel'].name, guess)


def test_movie_fromname(movies: dict[str, Movie]) -> None:
    video = Movie.fromname(movies['man_of_steel'].name)
    assert isinstance(video, Movie)
    assert video.name == movies['man_of_steel'].name
    assert video.source == movies['man_of_steel'].source
    assert video.release_group == movies['man_of_steel'].release_group
    assert video.resolution == movies['man_of_steel'].resolution
    assert video.video_codec == movies['man_of_steel'].video_codec
    assert video.audio_codec is None
    assert video.imdb_id is None
    assert video.hashes == {}
    assert video.size is None
    assert video.subtitle_languages == set()
    assert video.title == movies['man_of_steel'].title
    assert video.year == movies['man_of_steel'].year


def test_episode_fromname(episodes: dict[str, Episode]) -> None:
    video = Episode.fromname(episodes['bbt_s07e05'].name)
    assert isinstance(video, Episode)
    assert video.name == episodes['bbt_s07e05'].name
    assert video.source == episodes['bbt_s07e05'].source
    assert video.release_group == episodes['bbt_s07e05'].release_group
    assert video.resolution == episodes['bbt_s07e05'].resolution
    assert video.video_codec == episodes['bbt_s07e05'].video_codec
    assert video.audio_codec is None
    assert video.imdb_id is None
    assert video.hashes == {}
    assert video.size is None
    assert video.subtitle_languages == set()
    assert video.series == episodes['bbt_s07e05'].series
    assert video.season == episodes['bbt_s07e05'].season
    assert video.episode == episodes['bbt_s07e05'].episode
    assert video.title is None
    assert video.year is None
    assert video.tvdb_id is None


def test_episode_fromname_guessit_bug(episodes: dict[str, Episode]) -> None:
    # Only works with Video.fromname, not Episode.fromname
    video = Video.fromname(episodes['adam-12_s01e02'].name)
    assert isinstance(video, Episode)
    assert video.name == episodes['adam-12_s01e02'].name
    assert video.release_group == episodes['adam-12_s01e02'].release_group
    assert video.resolution == episodes['adam-12_s01e02'].resolution
    assert video.video_codec == episodes['adam-12_s01e02'].video_codec
    assert video.series == episodes['adam-12_s01e02'].series
    assert video.season == episodes['adam-12_s01e02'].season
    assert video.episode == episodes['adam-12_s01e02'].episode
    assert video.title is None
    assert video.year == episodes['adam-12_s01e02'].year
