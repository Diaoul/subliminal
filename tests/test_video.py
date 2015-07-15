# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from datetime import datetime, timedelta
import io
import os

from babelfish import Language
import pytest
from six import text_type as str
try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock

from subliminal.video import (Episode, Movie, Video, hash_opensubtitles, hash_thesubdb, scan_video, scan_videos,
                              search_external_subtitles)


def timestamp(date):
    """Get the timestamp of the `date`, python2/3 compatible

    :param datetime.datetime date: the utc date
    :return: the timestamp of the date
    :rtype: double

    """
    return (date - datetime(1970, 1, 1)).total_seconds()


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


def test_video_hash(episodes):
    video = episodes['bbt_s07e05']
    assert hash(video) == hash(video.name)


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


def test_search_external_subtitles(episodes, tmpdir):
    video_name = os.path.split(episodes['bbt_s07e05'].name)[1]
    video_root = os.path.splitext(video_name)[0]
    video_path = str(tmpdir.ensure(video_name))
    expected_subtitles = {
        video_name + '.srt': Language('und'),
        video_root + '.srt': Language('und'),
        video_root + '.en.srt': Language('eng'),
        video_name + '.fra.srt': Language('fra'),
        video_root + '.pt-BR.srt': Language('por', 'BR'),
        video_name + '.sr_cyrl.sub': Language('srp', script='Cyrl'),
        video_name + '.something.srt': Language('und')
    }
    tmpdir.ensure(os.path.split(episodes['got_s03e10'].name)[1] + '.srt')
    for path in expected_subtitles:
        tmpdir.ensure(path)
    subtitles = search_external_subtitles(video_path)
    assert subtitles == expected_subtitles


def test_search_external_subtitles_no_directory(movies, tmpdir, monkeypatch):
    video_name = os.path.split(movies['man_of_steel'].name)[1]
    video_root = os.path.splitext(video_name)[0]
    tmpdir.ensure(video_name)
    monkeypatch.chdir(str(tmpdir))
    expected_subtitles = {
        video_name + '.srt': Language('und'),
        video_root + '.en.srt': Language('eng')
    }
    for path in expected_subtitles:
        tmpdir.ensure(path)
    subtitles = search_external_subtitles(video_name)
    assert subtitles == expected_subtitles


def test_scan_video_movie(movies, tmpdir, monkeypatch):
    video = movies['man_of_steel']
    monkeypatch.chdir(str(tmpdir))
    tmpdir.ensure(video.name)
    scanned_video = scan_video(video.name)
    assert scanned_video.name == video.name
    assert scanned_video.format == video.format
    assert scanned_video.release_group == video.release_group
    assert scanned_video.resolution == video.resolution
    assert scanned_video.video_codec == video.video_codec
    assert scanned_video.audio_codec is None
    assert scanned_video.imdb_id is None
    assert scanned_video.hashes == {}
    assert scanned_video.size == 0
    assert scanned_video.subtitle_languages == set()
    assert scanned_video.title == video.title
    assert scanned_video.year == video.year


def test_scan_video_episode(episodes, tmpdir, monkeypatch):
    video = episodes['bbt_s07e05']
    monkeypatch.chdir(str(tmpdir))
    tmpdir.ensure(video.name)
    scanned_video = scan_video(video.name)
    assert scanned_video.name, video.name
    assert scanned_video.format == video.format
    assert scanned_video.release_group == video.release_group
    assert scanned_video.resolution == video.resolution
    assert scanned_video.video_codec == video.video_codec
    assert scanned_video.audio_codec is None
    assert scanned_video.imdb_id is None
    assert scanned_video.hashes == {}
    assert scanned_video.size == 0
    assert scanned_video.subtitle_languages == set()
    assert scanned_video.series == video.series
    assert scanned_video.season == video.season
    assert scanned_video.episode == video.episode
    assert scanned_video.title is None
    assert scanned_video.year is None
    assert scanned_video.tvdb_id is None


def test_scan_video_metadata(mkv):
    scanned_video = scan_video(mkv['test5'])
    assert type(scanned_video) is Movie
    assert scanned_video.name == mkv['test5']
    assert scanned_video.format is None
    assert scanned_video.release_group is None
    assert scanned_video.resolution is None
    assert scanned_video.video_codec == 'h264'
    assert scanned_video.audio_codec == 'AAC'
    assert scanned_video.imdb_id is None
    assert scanned_video.hashes == {'opensubtitles': '49e2530ea3bd0d18', 'thesubdb': '64a8b87f12daa4f31895616e6c3fd39e'}
    assert scanned_video.size == 31762747
    assert scanned_video.subtitle_languages == {Language('spa'), Language('deu'), Language('jpn'), Language('und'),
                                                Language('ita'), Language('fra'), Language('hun')}
    assert scanned_video.title == 'test5'
    assert scanned_video.year is None


def test_scan_video_path_does_not_exist(movies):
    with pytest.raises(ValueError) as excinfo:
        scan_video(movies['man_of_steel'].name)
    assert str(excinfo.value) == 'Path does not exist'


def test_scan_video_invalid_extension(movies, tmpdir, monkeypatch):
    monkeypatch.chdir(str(tmpdir))
    movie_name = os.path.splitext(movies['man_of_steel'].name)[0] + '.mp3'
    tmpdir.ensure(movie_name)
    with pytest.raises(ValueError) as excinfo:
        scan_video(movie_name)
    assert str(excinfo.value) == '.mp3 is not a valid video extension'


def test_scan_video_broken(mkv, tmpdir, monkeypatch):
    broken_path = 'test1.mkv'
    with io.open(mkv['test1'], 'rb') as original:
        with tmpdir.join(broken_path).open('wb') as broken:
            broken.write(original.read(512))
    monkeypatch.chdir(str(tmpdir))
    scanned_video = scan_video(broken_path)
    assert type(scanned_video) is Movie
    assert scanned_video.name == str(broken_path)
    assert scanned_video.format is None
    assert scanned_video.release_group is None
    assert scanned_video.resolution is None
    assert scanned_video.video_codec is None
    assert scanned_video.audio_codec is None
    assert scanned_video.imdb_id is None
    assert scanned_video.hashes == {}
    assert scanned_video.size == 512
    assert scanned_video.subtitle_languages == set()
    assert scanned_video.title == 'test1'
    assert scanned_video.year is None


def test_scan_videos_path_does_not_exist(movies):
    with pytest.raises(ValueError) as excinfo:
        scan_videos(movies['man_of_steel'].name)
    assert str(excinfo.value) == 'Path does not exist'


def test_scan_videos_path_is_not_a_directory(movies, tmpdir, monkeypatch):
    monkeypatch.chdir(str(tmpdir))
    tmpdir.ensure(movies['man_of_steel'].name)
    with pytest.raises(ValueError) as excinfo:
        scan_videos(movies['man_of_steel'].name)
    assert str(excinfo.value) == 'Path is not a directory'


def test_scan_videos(movies, tmpdir, monkeypatch):
    man_of_steel = tmpdir.ensure('movies', movies['man_of_steel'].name)
    tmpdir.ensure('movies', '.private', 'sextape.mkv')
    tmpdir.ensure('movies', '.hidden_video.mkv')
    tmpdir.ensure('movies', movies['enders_game'].name)
    tmpdir.ensure('movies', os.path.splitext(movies['enders_game'].name)[0] + '.nfo')
    tmpdir.ensure('movies', 'watched', dir=True)
    tmpdir.join('movies', 'watched', os.path.split(movies['man_of_steel'].name)[1]).mksymlinkto(man_of_steel)

    mock_scan_video = Mock()
    monkeypatch.setattr('subliminal.video.scan_video', mock_scan_video)
    monkeypatch.chdir(str(tmpdir))
    videos = scan_videos('movies')

    kwargs = dict(subtitles=True, embedded_subtitles=True)
    calls = [((os.path.join('movies', movies['man_of_steel'].name),), kwargs),
             ((os.path.join('movies', movies['enders_game'].name),), kwargs)]
    assert len(videos) == len(calls)
    assert mock_scan_video.call_count == len(calls)
    mock_scan_video.assert_has_calls(calls, any_order=True)


def test_hash_opensubtitles(mkv):
    assert hash_opensubtitles(mkv['test1']) == '40b44a7096b71ec3'


def test_hash_opensubtitles_too_small(tmpdir):
    path = tmpdir.ensure('test_too_small.mkv')
    assert hash_opensubtitles(str(path)) is None


def test_hash_thesubdb(mkv):
    assert hash_thesubdb(mkv['test1']) == '054e667e93e254f8fa9f9e8e6d4e73ff'


def test_hash_thesubdb_too_small(tmpdir):
    path = tmpdir.ensure('test_too_small.mkv')
    assert hash_thesubdb(str(path)) is None
