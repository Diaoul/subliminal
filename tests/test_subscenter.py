# -*- coding: utf-8 -*-
import os

from babelfish import Language
import pytest
from vcr import VCR

from subliminal.exceptions import ConfigurationError, AuthenticationError
from subliminal.providers.subscenter import SubsCenterProvider, SubsCenterSubtitle


vcr = VCR(path_transformer=lambda path: path + '.yaml',
          record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
          match_on=['method', 'scheme', 'host', 'port', 'path', 'query', 'body'],
          cassette_library_dir=os.path.join('tests', 'cassettes', 'subscenter'))


def test_get_matches_movie(movies):
    releases = ['Enders.Game.2013.HC.Webrip.x264.AC3-TiTAN', 'Enders.Game.2013.KORSUB.HDRip.XViD-NO1KNOWS',
                'Enders.Game.2013.KORSUB.HDRip.h264.AAC-RARBG', 'Enders.Game.2013.HDRip.XViD.AC3-ReLeNTLesS',
                'Enders.Game.2013.720p.KOR.HDRip.H264-KTH']
    subtitle = SubsCenterSubtitle(Language('heb'), False, None, None, None, None, 'Ender\'s Game', 266898,
                                  '54adce017db2e7fd8501b7a321451b64', 389, releases)
    matches = subtitle.get_matches(movies['enders_game'])
    assert matches == {'title', 'year', 'resolution', 'video_codec'}


def test_get_matches_episode(episodes):
    releases = ['Game.of.Thrones.S03E10.HDTV.x264-EVOLVE']
    subtitle = SubsCenterSubtitle(Language('heb'), False, None, 'Game of Thrones', 3, 10, 'Mhysa', 263129,
                                  '6a3129e8b9effdb8231aa6b3caf66fbe', 6706, releases)
    matches = subtitle.get_matches(episodes['got_s03e10'])
    assert matches == {'series', 'episode', 'season', 'title', 'year', 'video_codec'}


def test_get_matches_no_match(movies):
    releases = ['Game.of.Thrones.S03E10.HDTV.EVOLVE']
    subtitle = SubsCenterSubtitle(Language('heb'), False, None, 'Game of Thrones', 3, 10, 'Mhysa', 263129,
                                  '6a3129e8b9effdb8231aa6b3caf66fbe', 6706, releases)
    matches = subtitle.get_matches(movies['man_of_steel'])
    assert matches == set()


def test_configuration_error_no_username():
    with pytest.raises(ConfigurationError):
        SubsCenterProvider(password='subliminal')


def test_configuration_error_no_password():
    with pytest.raises(ConfigurationError):
        SubsCenterProvider(username='subliminal')


@pytest.mark.integration
@vcr.use_cassette
def test_login():
    provider = SubsCenterProvider('subliminal@gmail.com', 'subliminal')
    assert not provider.logged_in
    provider.initialize()
    assert provider.logged_in


@pytest.mark.integration
@vcr.use_cassette
def test_login_bad_password():
    provider = SubsCenterProvider('subliminal@gmail.com', 'lanimilbus')
    with pytest.raises(AuthenticationError):
        provider.initialize()


@pytest.mark.integration
@vcr.use_cassette
def test_logout():
    provider = SubsCenterProvider('subliminal@gmail.com', 'subliminal')
    provider.initialize()
    provider.terminate()
    assert not provider.logged_in


@pytest.mark.integration
@vcr.use_cassette
def test_search_url_title_episode(episodes):
    video = episodes['dallas_2012_s01e03']
    with SubsCenterProvider() as provider:
        url_title = provider._search_url_title(video.series, 'series')
    assert url_title == 'dallas'


@pytest.mark.integration
@vcr.use_cassette
def test_search_url_title_movies(movies):
    video = movies['man_of_steel']
    with SubsCenterProvider() as provider:
        url_title = provider._search_url_title(video.title, 'movie')
    assert url_title == 'superman-man-of-steel'


@pytest.mark.integration
@vcr.use_cassette
def test_query_movie(movies):
    video = movies['enders_game']
    expected_subtitles = {'267118', '266898', '267140'}
    with SubsCenterProvider() as provider:
        subtitles = provider.query(title=video.title)
    assert len(subtitles) == len(expected_subtitles)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles


@pytest.mark.integration
@vcr.use_cassette
def test_query_episode(episodes):
    video = episodes['dallas_2012_s01e03']
    expected_subtitles = {'264417', '256843', '256842'}
    with SubsCenterProvider() as provider:
        subtitles = provider.query(series=video.series, season=video.season, episode=video.episode)
    assert len(subtitles) == len(expected_subtitles)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_movie(movies):
    video = movies['man_of_steel']
    languages = {Language('heb')}
    expected_subtitles = {'263600', '263610', '263628', '263607', '263470', '263609', '263630', '263481', '263627',
                          '263493', '265320', '263608', '263479'}
    with SubsCenterProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert len(subtitles) == len(expected_subtitles)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_episode(episodes):
    video = episodes['got_s03e10']
    languages = {Language('heb')}
    expected_subtitles = {'263128', '263129', '263127', '263139', '263130'}
    with SubsCenterProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert len(subtitles) == len(expected_subtitles)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle(movies):
    video = movies['enders_game']
    languages = {Language('heb')}
    with SubsCenterProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        provider.download_subtitle(subtitles[0])
    assert subtitles[0].content is not None
    assert subtitles[0].is_valid() is True
