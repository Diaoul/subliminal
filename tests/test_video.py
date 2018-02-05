# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

import pytest
from six import text_type as str
try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock

from subliminal.utils import sanitize, timestamp
from subliminal.video import Episode, Movie, Video


def test_video_exists_age(movies, tmpdir, monkeypatch):
    monkeypatch.chdir(str(tmpdir))
    video = movies['man_of_steel']
    tmpdir.ensure(video.name).setmtime(timestamp(datetime.utcnow() - timedelta(days=3)))
    assert video.exists
    assert timedelta(days=3) < video.age < timedelta(days=3, seconds=1)


def test_video_age(movies):
    assert movies['man_of_steel'].age == timedelta()


def test_video_fromguess_episode(episodes, monkeypatch):
    guess = {'type': 'episode'}
    monkeypatch.setattr(Episode, 'fromguess', Mock())
    Video.fromguess(episodes['bbt_s07e05'].name, guess)
    assert Episode.fromguess.called


def test_video_fromguess_movie(movies, monkeypatch):
    guess = {'type': 'movie'}
    monkeypatch.setattr(Movie, 'fromguess', Mock())
    Video.fromguess(movies['man_of_steel'].name, guess)
    assert Movie.fromguess.called


def test_video_fromguess_wrong_type(episodes):
    guess = {'type': 'subtitle'}
    with pytest.raises(ValueError) as excinfo:
        Video.fromguess(episodes['bbt_s07e05'].name, guess)
    assert str(excinfo.value) == 'The guess must be an episode or a movie guess'


def test_video_fromname_movie(movies):
    video = Video.fromname(movies['man_of_steel'].name)
    assert type(video) is Movie
    assert video.name == movies['man_of_steel'].name
    assert video.format == movies['man_of_steel'].format
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


def test_video_fromname_episode(episodes):
    video = Video.fromname(episodes['bbt_s07e05'].name)
    assert type(video) is Episode
    assert video.name == episodes['bbt_s07e05'].name
    assert video.format == episodes['bbt_s07e05'].format
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


def test_video_fromname_episode_no_season(episodes):
    video = Video.fromname(episodes['the_jinx_e05'].name)
    assert type(video) is Episode
    assert video.name == episodes['the_jinx_e05'].name
    assert video.format == episodes['the_jinx_e05'].format
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


def test_video_hash(episodes):
    video = episodes['bbt_s07e05']
    assert hash(video) == hash(video.name)


def test_episode_from_guess_multi_episode(episodes):
    video = Video.fromname(episodes['Marvels.Agents.of.S.H.I.E.L.D.S05E01-E02'].name)
    # Multi-ep is converted to single-ep by taking the lowest episode number
    assert video.episode == episodes['Marvels.Agents.of.S.H.I.E.L.D.S05E01-E02'].episode


def test_episode_fromguess_wrong_type(episodes):
    guess = {'type': 'subtitle'}
    with pytest.raises(ValueError) as excinfo:
        Episode.fromguess(episodes['bbt_s07e05'].name, guess)
    assert str(excinfo.value) == 'The guess must be an episode guess'


def test_episode_fromguess_insufficient_data(episodes):
    guess = {'type': 'episode'}
    with pytest.raises(ValueError) as excinfo:
        Episode.fromguess(episodes['bbt_s07e05'].name, guess)
    assert str(excinfo.value) == 'Insufficient data to process the guess'


def test_movie_fromguess_wrong_type(movies):
    guess = {'type': 'subtitle'}
    with pytest.raises(ValueError) as excinfo:
        Movie.fromguess(movies['man_of_steel'].name, guess)
    assert str(excinfo.value) == 'The guess must be a movie guess'


def test_movie_fromguess_insufficient_data(movies):
    guess = {'type': 'movie'}
    with pytest.raises(ValueError) as excinfo:
        Movie.fromguess(movies['man_of_steel'].name, guess)
    assert str(excinfo.value) == 'Insufficient data to process the guess'


def test_movie_fromname(movies):
    video = Movie.fromname(movies['man_of_steel'].name)
    assert video.name == movies['man_of_steel'].name
    assert video.format == movies['man_of_steel'].format
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


def test_episode_fromname(episodes):
    video = Episode.fromname(episodes['bbt_s07e05'].name)
    assert video.name == episodes['bbt_s07e05'].name
    assert video.format == episodes['bbt_s07e05'].format
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
