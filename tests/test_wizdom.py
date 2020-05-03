# -*- coding: utf-8 -*-
import os

from babelfish import Language
import pytest
from vcr import VCR

from subliminal.providers.wizdom import WizdomProvider, WizdomSubtitle


vcr = VCR(path_transformer=lambda path: path + '.yaml',
          record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
          match_on=['method', 'scheme', 'host', 'port', 'path', 'query', 'body'],
          cassette_library_dir=os.path.realpath(os.path.join('tests', 'cassettes', 'wizdom')))


def test_get_matches_movie(movies):
    release = 'Enders.Game.2013.720p.BluRay.x264-SPARKS'
    subtitle = WizdomSubtitle(Language('heb'), False, None, None, None, None, 'Ender\'s Game', 'tt1731141',
                              '18947', release)
    matches = subtitle.get_matches(movies['enders_game'])
    assert matches == {'country', 'title', 'year', 'resolution', 'video_codec', 'source', 'release_group'}


def test_get_matches_episode(episodes):
    release = 'Game.of.Thrones.S03E10.720p.HDTV.x264-EVOLVE'
    subtitle = WizdomSubtitle(Language('heb'), False, None, 'Game of Thrones', 3, 10, 'Mhysa', 'tt0944947',
                              '3748', release)
    matches = subtitle.get_matches(episodes['got_s03e10'])
    assert matches == {'series', 'episode', 'season', 'video_codec', 'resolution', 'series_imdb_id'}


def test_get_matches_no_match(movies):
    release = 'Game.of.Thrones.S03E10.720p.HDTV.x264-EVOLVE'
    subtitle = WizdomSubtitle(Language('heb'), False, None, 'Game of Thrones', 3, 10, 'Mhysa', 'tt0944947',
                              '3748', release)
    matches = subtitle.get_matches(movies['man_of_steel'])
    assert matches == {'country', 'video_codec', 'resolution'}


@pytest.mark.integration
@vcr.use_cassette
def test_search_imdb_id_episode(episodes):
    video = episodes['dallas_2012_s01e03']
    with WizdomProvider() as provider:
        imdb_id = provider._search_imdb_id(video.series, 0, False)
    assert imdb_id == 'tt0077000'


@pytest.mark.integration
@vcr.use_cassette
def test_search_imdb_id_movies(movies):
    video = movies['man_of_steel']
    with WizdomProvider() as provider:
        imdb_id = provider._search_imdb_id(video.title, 2013, True)
    assert imdb_id == 'tt0770828'


@pytest.mark.integration
@vcr.use_cassette
def test_search_imdb_id_no_suggestion():
    with WizdomProvider() as provider:
        imdb_id = provider._search_imdb_id('This is a test', 0, False)
    assert imdb_id is None


@pytest.mark.integration
@vcr.use_cassette
def test_query_movie(movies):
    video = movies['enders_game']
    expected_subtitles = {'18946', '18947', '18948', '18949', '18950', '18951', '18952', '18953', '18954', '18955',
                          '18956', '18957', '18958', '18960', '18961', '18962', '18963', '18964', '18965', '18966',
                          '18967', '18968', '18969', '18970', '18971', '18972', '18973', '18974', '18975', '18976',
                          '18977', '18978', '18979', '18980', '18981', '18982', '18983', '18984', '18985', '18986',
                          '18987', '18988', '18989', '18990'}
    with WizdomProvider() as provider:
        subtitles = provider.query(video.title)
    assert len(subtitles) == len(expected_subtitles)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles


@pytest.mark.integration
@vcr.use_cassette
def test_query_episode(episodes):
    video = episodes['bbt_s07e05']
    expected_subtitles = {'63493', '71181', '64827', '68933', '90478', '90479', '111527', '74952', '68821', '68822',
                          '39895', '69621'}
    with WizdomProvider() as provider:
        subtitles = provider.query(video.series, season=video.season, episode=video.episode)
    assert len(subtitles) == len(expected_subtitles)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_movie(movies):
    video = movies['man_of_steel']
    languages = {Language('heb')}
    expected_subtitles = {'185106', '24351', '24353', '24355', '24357', '24359', '24361', '24363', '24366', '24368',
                          '24370', '24372', '24374', '24376', '24378', '24380', '95805', '24382', '24384', '24386',
                          '24388', '24390', '24392', '24394', '24396', '62796', '62797', '24398', '24400', '24402',
                          '24404', '24405', '24408', '24410', '90978', '64634', '114837', '77724', '134085', '134088',
                          '75722', '134091', '155340', '66283'}
    with WizdomProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert len(subtitles) == len(expected_subtitles)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_episode(episodes):
    video = episodes['got_s03e10']
    languages = {Language('heb')}
    expected_subtitles = {'166995', '46192', '39541', '40067', '40068', '4231', '4232', '3748', '71362', '61901'}
    with WizdomProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert len(subtitles) == len(expected_subtitles)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_episode_alternative_series(episodes):
    video = episodes['turn_s04e03']
    languages = {Language('heb')}
    expected_subtitles = {'187862'}
    with WizdomProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert len(subtitles) == len(expected_subtitles)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle(movies):
    video = movies['enders_game']
    languages = {Language('heb')}
    with WizdomProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        provider.download_subtitle(subtitles[0])
    assert subtitles[0].content is not None
    assert subtitles[0].is_valid() is True
