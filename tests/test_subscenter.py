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
    subtitle = SubsCenterSubtitle(Language('heb'), None, 0, 0, 'Man of Steel',
                                  'Man.of.Steel.German.720p.BluRay.x264-EXQUiSiTE', 'movie', False, None, None)
    matches = subtitle.get_matches(movies['man_of_steel'])
    assert matches == {'title', 'video_codec', 'resolution', 'format', 'hearing_impaired'}


def test_get_matches_episode(episodes):
    subtitle = SubsCenterSubtitle(Language('heb'), 'Game of Thrones', 3, 10, 'Mhysa',
                                  'Game.of.Thrones.S03E10.HDTV.XviD-AFG', 'episode', False, None, None)
    matches = subtitle.get_matches(episodes['got_s03e10'])
    assert matches == {'series', 'episode', 'season', 'title', 'year', 'hearing_impaired'}


def test_get_matches_no_match(episodes):
    subtitle = SubsCenterSubtitle(Language('heb'), None, 0, 0, 'Man of Steel',
                                  'man.of.steel.2013.720p.bluray.x264-felony', 'movie', False, None, None)
    matches = subtitle.get_matches(episodes['got_s03e10'], hearing_impaired=True)
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
def test_query_query_movie(movies):
    video = movies['enders_game']
    languages = {Language('heb')}
    expected_subtitles = {
        'http://subscenter.cinemast.com/he/subtitle/download/he/267140/?v=Enders.Game.2013.480p.BluRay.x264-mSD&key='
        '03ab6a943e732ad6d9941884bd7884c5',
        'http://subscenter.cinemast.com/he/subtitle/download/he/267140/?v=Enders.Game.(2013).720p.BluRAY.800MB-Micro'
        'mkv&key=fa7b4cd387e784b1d54289260db1e45c',
        'http://subscenter.cinemast.com/he/subtitle/download/he/267140/?v=Enders.Game.2013.1080p.BluRay.DTS.x264-Pub'
        'licHD&key=6fddf17ce5c7bc264e983e657a862b76',
        'http://subscenter.cinemast.com/he/subtitle/download/he/267140/?v=Enders.Game.2013.BRRip.XviD.AC3-RARBG&key='
        'd4f8ab0d2cc32809c84ca722cad28285'
    }
    with SubsCenterProvider() as provider:
        subtitles = provider.query(languages, title=video.title)
    assert len(expected_subtitles.intersection({subtitle.id for subtitle in subtitles})) == len(expected_subtitles)
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_query_query_episode(episodes):
    video = episodes['dallas_2012_s01e03']
    languages = {Language('heb')}
    expected_subtitles = {
        'http://subscenter.cinemast.com/he/subtitle/download/he/264417/?v=Dallas.2012.S01E03.DVDRip.XviD-REWARD&key='
        'a0ed1cb02d51b74849aaf2eaa7fc65ba',
        'http://subscenter.cinemast.com/he/subtitle/download/he/256843/?v=Dallas.2012.S01E03.480p.HDTV.x264-mSD&key='
        '6afae8894c7a3a947f3ce460e3ea1cc5',
        'http://subscenter.cinemast.com/he/subtitle/download/he/256843/?v=Dallas.2012.S01E03.HDTV.XviD-AFG&key=a1138'
        'da829d83763b53d2c9a6c1ed6fd',
        'http://subscenter.cinemast.com/he/subtitle/download/he/256842/?v=Dallas.2012.S01E03.720p.HDTV.X264-DIMENSIO'
        'N&key=19596f9beba1bdbfa0232282e43baa60',
        'http://subscenter.cinemast.com/he/subtitle/download/he/256842/?v=Dallas.2012.S01E03.HDTV.x264-LOL&key=00ee3'
        '02fce779d97bc8654f23bb961e0'
    }
    with SubsCenterProvider() as provider:
        subtitles = provider.query(languages, series=video.series, season=video.season, episode=video.episode)
    assert len(expected_subtitles.difference({subtitle.id for subtitle in subtitles})) == 0
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_query_query_season_episode(episodes):
    video = episodes['bbt_s07e05']
    languages = {Language('heb')}
    expected_subtitles = {
        'http://subscenter.cinemast.com/he/subtitle/download/he/265237/?v=The.Big.Bang.Theory.S07E05.HDTV.x264-LOL&'
        'key=146367a10dcaac068ae571a53b7687f4',
        'http://subscenter.cinemast.com/he/subtitle/download/he/265237/?v=The.Big.Bang.Theory.S07E05.HDTV.XviD-AFG&'
        'key=0e277eac84cf2bd314dcd189e38242aa',
        'http://subscenter.cinemast.com/he/subtitle/download/he/265237/?v=The.Big.Bang.Theory.S07E05.720p.HDTV.X264'
        '-DIMENSION&key=ce8e4086da2688eb6ab183c0d831e855',
        'http://subscenter.cinemast.com/he/subtitle/download/he/265237/?v=The.Big.Bang.Theory.S07E05.480p.HDTV.85MB'
        '-Micromkv&key=7b4535ebaabbe99d20965e9e12cb1ac3',
        'http://subscenter.cinemast.com/he/subtitle/download/he/265237/?v=The.Big.Bang.Theory.S07E05.HDTV.x264-Cham'
        'eE&key=a1e13022bbff7bfe5fb073f4dd2696af',
        'http://subscenter.cinemast.com/he/subtitle/download/he/265237/?v=The.Big.Bang.Theory.S07E05.480p.HDTV.x264'
        '-mSD&key=2c3a61c6d73dbfe293a5d5d434a326c9'
    }
    with SubsCenterProvider() as provider:
        subtitles = provider.query(languages, series=video.series, season=video.season, episode=video.episode)
    assert len(expected_subtitles.difference({subtitle.id for subtitle in subtitles})) == 0
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_movie(movies):
    video = movies['enders_game']
    languages = {Language('heb')}
    expected_subtitles = {
        'http://subscenter.cinemast.com/he/subtitle/download/he/267140/?v=Enders.Game.2013.480p.BluRay.x264-mSD&key'
        '=03ab6a943e732ad6d9941884bd7884c5',
        'http://subscenter.cinemast.com/he/subtitle/download/he/267140/?v=Enders.Game.(2013).720p.BluRAY.800MB-Micr'
        'omkv&key=fa7b4cd387e784b1d54289260db1e45c',
        'http://subscenter.cinemast.com/he/subtitle/download/he/267140/?v=Enders.Game.2013.1080p.BluRay.DTS.x264-Pu'
        'blicHD&key=6fddf17ce5c7bc264e983e657a862b76',
        'http://subscenter.cinemast.com/he/subtitle/download/he/267140/?v=Enders.Game.2013.BRRip.XviD.AC3-RARBG&key'
        '=d4f8ab0d2cc32809c84ca722cad28285'
    }
    with SubsCenterProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert len(expected_subtitles.intersection({subtitle.id for subtitle in subtitles})) == len(expected_subtitles)
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_episode(episodes):
    video = episodes['bbt_s07e05']
    languages = {Language('heb')}
    expected_subtitles = {
        'http://subscenter.cinemast.com/he/subtitle/download/he/265237/?v=The.Big.Bang.Theory.S07E05.HDTV.x264-LOL&'
        'key=146367a10dcaac068ae571a53b7687f4',
        'http://subscenter.cinemast.com/he/subtitle/download/he/265237/?v=The.Big.Bang.Theory.S07E05.HDTV.XviD-AFG&'
        'key=0e277eac84cf2bd314dcd189e38242aa',
        'http://subscenter.cinemast.com/he/subtitle/download/he/265237/?v=The.Big.Bang.Theory.S07E05.720p.HDTV.X264'
        '-DIMENSION&key=ce8e4086da2688eb6ab183c0d831e855',
        'http://subscenter.cinemast.com/he/subtitle/download/he/265237/?v=The.Big.Bang.Theory.S07E05.480p.HDTV.85MB'
        '-Micromkv&key=7b4535ebaabbe99d20965e9e12cb1ac3',
        'http://subscenter.cinemast.com/he/subtitle/download/he/265237/?v=The.Big.Bang.Theory.S07E05.HDTV.x264-Cham'
        'eE&key=a1e13022bbff7bfe5fb073f4dd2696af',
        'http://subscenter.cinemast.com/he/subtitle/download/he/265237/?v=The.Big.Bang.Theory.S07E05.480p.HDTV.x264'
        '-mSD&key=2c3a61c6d73dbfe293a5d5d434a326c9'
    }
    with SubsCenterProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert len(expected_subtitles.difference({subtitle.id for subtitle in subtitles})) == 0
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
