# -*- coding: utf-8 -*-
import os

from babelfish import Language
import pytest
from vcr import VCR

from subliminal.exceptions import ConfigurationError, AuthenticationError
from subliminal.providers.cinemast import CinemastProvider, CinemastSubtitle

DEFAULT_USERNAME = 'subliminal@gmail.com'
DEFAULT_PASSWORD = 'subliminal'

vcr = VCR(path_transformer=lambda path: path + '.yaml',
          record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
          match_on=['method', 'scheme', 'host', 'port', 'path', 'query', 'body'],
          cassette_library_dir=os.path.realpath(os.path.join('tests', 'cassettes', 'cinemast')))


def test_get_matches_movie(movies):
    subtitle = CinemastSubtitle(Language('heb'), None, None, None, None, 'Ender\'s Game', 266898,
                                '54adce017db2e7fd8501b7a321451b64', 'Enders.Game.2013.HC.Webrip.x264.AC3-TiTAN')
    matches = subtitle.get_matches(movies['enders_game'])
    assert matches == {'country', 'title', 'video_codec', 'year'}


def test_get_matches_episode(episodes):
    subtitle = CinemastSubtitle(Language('heb'), None, 'Game of Thrones', 3, 10, 'Mhysa', 263129,
                                '6a3129e8b9effdb8231aa6b3caf66fbe', 'Game.of.Thrones.S03E10.HDTV.x264-EVOLVE')
    matches = subtitle.get_matches(episodes['got_s03e10'])
    assert matches == {'episode', 'season', 'series', 'video_codec'}


def test_get_matches_no_match(episodes):
    subtitle = CinemastSubtitle(Language('heb'), None, None, None, None, 'Ender\'s Game', 266898,
                                '54adce017db2e7fd8501b7a321451b64', 'Enders.Game.2013-TiTAN')
    matches = subtitle.get_matches(episodes['got_s03e10'])
    assert matches == set()


def test_configuration_error_no_username():
    with pytest.raises(ConfigurationError):
        CinemastProvider(password=DEFAULT_PASSWORD)


def test_configuration_error_no_password():
    with pytest.raises(ConfigurationError):
        CinemastProvider(username=DEFAULT_USERNAME)


@pytest.mark.integration
@vcr.use_cassette
def test_login():
    provider = CinemastProvider(username=DEFAULT_USERNAME, password=DEFAULT_PASSWORD)
    assert not provider.token
    provider.initialize()
    assert provider.token


@pytest.mark.integration
@vcr.use_cassette
def test_login_bad_password():
    provider = CinemastProvider(username=DEFAULT_USERNAME, password='lanimilbus')
    with pytest.raises(AuthenticationError):
        provider.initialize()


@pytest.mark.integration
@vcr.use_cassette
def test_logout():
    provider = CinemastProvider(username=DEFAULT_USERNAME, password=DEFAULT_PASSWORD)
    provider.initialize()
    provider.terminate()
    assert not provider.token


@pytest.mark.integration
@vcr.use_cassette
def test_query_movie(movies):
    video = movies['enders_game']
    expected_subtitles = {'267118', '266898', '267140'}
    with CinemastProvider(username=DEFAULT_USERNAME, password=DEFAULT_PASSWORD) as provider:
        subtitles = provider.query(video.title)
    assert len(subtitles) == len(expected_subtitles)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles


@pytest.mark.integration
@vcr.use_cassette
def test_query_episode(episodes):
    video = episodes['dallas_2012_s01e03']
    expected_subtitles = {'264417', '256843', '256842'}
    with CinemastProvider(username=DEFAULT_USERNAME, password=DEFAULT_PASSWORD) as provider:
        subtitles = provider.query(video.series, season=video.season, episode=video.episode)
    assert len(subtitles) == len(expected_subtitles)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_movie(movies):
    video = movies['man_of_steel']
    languages = {Language('heb')}
    expected_subtitles = {'263600', '263610', '263628', '263607', '263470', '263609', '263630', '263481', '263627',
                          '263493', '265320', '263608', '263479'}
    with CinemastProvider(username=DEFAULT_USERNAME, password=DEFAULT_PASSWORD) as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert len(subtitles) == len(expected_subtitles)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_episode(episodes):
    video = episodes['got_s03e10']
    languages = {Language('heb')}
    expected_subtitles = {'263128', '290133', '263129', '263127', '263139', '263130'}
    with CinemastProvider(username=DEFAULT_USERNAME, password=DEFAULT_PASSWORD) as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert len(subtitles) == len(expected_subtitles)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_episode_alternative_series(episodes):
    video = episodes['turn_s04e03']
    languages = {Language('heb')}
    expected_subtitles = {'289777', '289099'}
    with CinemastProvider(username=DEFAULT_USERNAME, password=DEFAULT_PASSWORD) as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert len(subtitles) == len(expected_subtitles)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle(movies):
    video = movies['enders_game']
    languages = {Language('heb')}
    with CinemastProvider(username=DEFAULT_USERNAME, password=DEFAULT_PASSWORD) as provider:
        subtitles = provider.list_subtitles(video, languages)
        provider.download_subtitle(subtitles[0])
    assert subtitles[0].content is not None
    assert subtitles[0].is_valid() is True
