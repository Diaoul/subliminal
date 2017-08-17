# -*- coding: utf-8 -*-
import os.path

from babelfish import Language
import pytest
from vcr import VCR

from subliminal.exceptions import AuthenticationError, ConfigurationError
from subliminal.providers import Episode
from subliminal.providers.itasa import ItaSAProvider, ItaSASubtitle


vcr = VCR(path_transformer=lambda path: path + '.yaml',
          record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
          match_on=['method', 'scheme', 'host', 'port', 'path', 'query', 'body'],
          cassette_library_dir=os.path.join('tests', 'cassettes', 'itasa'),
          filter_query_parameters=['username', 'password'],
          filter_post_data_parameters=['username', 'passwd'])
test_user = 'subliminal-test'
test_password = 'subliminal-test'


def test_get_matches_season_episode_resolution_tvdb(episodes):
    subtitle = ItaSASubtitle(5514, 'The Big Bang Theory', 7, 5, '720p', 2007, 80379,
                             'The.Big.Bang.Theory.s07e05.720p.sub.itasa.srt')
    matches = subtitle.get_matches(episodes['bbt_s07e05'])
    assert matches == {'series', 'season', 'episode', 'resolution', 'year',  'series_tvdb_id'}


def test_get_matches_season_episode_resolution(episodes):
    subtitle = ItaSASubtitle(5514, 'The Big Bang Theory', 7, 5, '720p', None, None,
                             'The.Big.Bang.Theory.s07e05.720p.sub.itasa.srt')
    matches = subtitle.get_matches(episodes['bbt_s07e05'])
    assert matches == {'series', 'season', 'episode', 'resolution'}


def test_get_matches_season_episode(episodes):
    subtitle = ItaSASubtitle(5514, 'The Big Bang Theory', 7, 5, 'HDTV', None, None,
                             'The.Big.Bang.Theory.s07e05.sub.itasa.srt')
    matches = subtitle.get_matches(episodes['bbt_s07e05'])
    assert matches == {'series', 'season', 'episode', 'format'}


def test_get_matches_no_match(episodes):
    subtitle = ItaSASubtitle(5514, 'The Big Bang Theory', 7, 5, 'HDTV', None, None,
                             'The.Big.Bang.Theory.s07e05.sub.itasa.srt')
    matches = subtitle.get_matches(episodes['got_s03e10'])
    assert matches == set([])


def test_configuration_error_no_username():
    with pytest.raises(ConfigurationError):
        ItaSAProvider(password=test_password)


def test_configuration_error_no_password():
    with pytest.raises(ConfigurationError):
        ItaSAProvider(username=test_user)


@pytest.mark.integration
@vcr.use_cassette
def test_login():
    provider = ItaSAProvider(test_user, test_password)
    assert provider.logged_in is False
    provider.initialize()
    assert provider.logged_in is True


@pytest.mark.integration
@vcr.use_cassette
def test_login_bad_password():
    provider = ItaSAProvider(test_user, 'tset-lanimilbus')
    with pytest.raises(AuthenticationError):
        provider.initialize()


@pytest.mark.integration
@vcr.use_cassette
def test_logout():
    provider = ItaSAProvider(test_user, test_password)
    provider.initialize()
    provider.terminate()
    assert provider.logged_in is False


@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id():
    with ItaSAProvider() as provider:
        show_id = provider._search_show_id('The Big Bang Theory')
    assert show_id == 399


@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id_incomplete():
    with ItaSAProvider() as provider:
        show_id = provider._search_show_id('The Big Bang')
    assert show_id is None


@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id2():
    with ItaSAProvider() as provider:
        show_id = provider._search_show_id('Dallas')
    assert show_id == 3420


@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id_error():
    with ItaSAProvider() as provider:
        show_id = provider._search_show_id('The Big How I Met Your Mother')
    assert show_id is None


@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id_quote():
    with ItaSAProvider() as provider:
        show_id = provider._search_show_id('Grey\'s Anatomy')
    assert show_id == 79


@pytest.mark.integration
@vcr.use_cassette('test_get_show_ids')
def test_get_show_ids():
    with ItaSAProvider() as provider:
        show_ids = provider._get_show_ids()
    assert 'the big bang theory' in show_ids
    assert show_ids['the big bang theory'] == 399


@pytest.mark.integration
@vcr.use_cassette('test_get_show_ids')
def test_get_show_ids2():
    with ItaSAProvider() as provider:
        show_ids = provider._get_show_ids()
    assert 'dallas' in show_ids
    assert show_ids['dallas'] == 3420


@pytest.mark.integration
@vcr.use_cassette('test_get_show_ids')
def test_get_show_ids_dot():
    with ItaSAProvider() as provider:
        show_ids = provider._get_show_ids()
    assert 'mr robot' in show_ids
    assert show_ids['mr robot'] == 5881


@pytest.mark.integration
@vcr.use_cassette('test_get_show_ids')
def test_get_show_ids_country():
    with ItaSAProvider() as provider:
        show_ids = provider._get_show_ids()
    assert 'being human us' in show_ids
    assert show_ids['being human us'] == 2350


@pytest.mark.integration
@vcr.use_cassette('test_get_show_ids')
def test_get_show_ids_quote():
    with ItaSAProvider() as provider:
        show_ids = provider._get_show_ids()
    assert 'marvels agents of s h i e l d' in show_ids
    assert show_ids['marvels agents of s h i e l d'] == 4430


@pytest.mark.integration
@vcr.use_cassette
def test_get_show_id_quote_dots_mixed_case(episodes):
    video = episodes['marvels_agents_of_shield_s02e06']
    with ItaSAProvider() as provider:
        show_id = provider.get_show_id(video.series)
    assert show_id == 4430


@pytest.mark.integration
@vcr.use_cassette
def test_get_show_id_country():
    with ItaSAProvider() as provider:
        show_id = provider.get_show_id('Being Human', country_code='US')
    assert show_id == 2350


@pytest.mark.integration
@vcr.use_cassette
def test_get_show_id():
    with ItaSAProvider() as provider:
        show_id = provider.get_show_id('Dallas')
    assert show_id == 3420


@pytest.mark.integration
@vcr.use_cassette
def test_query(episodes):
    video = episodes['bbt_s07e05']
    with ItaSAProvider(test_user, test_password) as provider:
        provider.initialize()
        subtitles = provider.query(video.series, video.season, video.episode, video.format, video.resolution)
    assert len(subtitles) == 1
    # print subtitles[0].id
    for subtitle in subtitles:
        assert subtitle.series == video.series
        assert subtitle.season == video.season
        assert subtitle.episode == video.episode
        assert subtitle.format == video.format
        assert len(subtitle.content) == 28443


@pytest.mark.integration
@vcr.use_cassette
def test_query_wrong_series(episodes):
    video = episodes['bbt_s07e05']
    with ItaSAProvider(test_user, test_password) as provider:
        provider.initialize()
        subtitles = provider.query(video.series[:12], video.season, video.episode, video.format, video.resolution)
    assert len(subtitles) == 0


@pytest.mark.integration
@vcr.use_cassette
def test_query_parsing(episodes):
    video = episodes['got_s03e10']
    with ItaSAProvider(test_user, test_password) as provider:
        provider.initialize()
        subtitles = provider.query(video.series, video.season, video.episode, video.format, video.resolution)
    subtitle = subtitles[0]
    assert subtitle.language == Language('ita')
    assert subtitle.page_link is None
    assert subtitle.series == video.series
    assert subtitle.season == video.season
    assert subtitle.episode == video.episode
    assert subtitle.format == 'WEB-DL'


@pytest.mark.integration
@vcr.use_cassette
def test_query_parsing_quote_dots_mixed_case(episodes):
    video = episodes['marvels_agents_of_shield_s02e06']
    with ItaSAProvider(test_user, test_password) as provider:
        provider.initialize()
        subtitles = provider.query(video.series, video.season, video.episode, video.format, video.resolution)
    subtitle = subtitles[0]
    assert subtitle.language == Language('ita')
    assert subtitle.page_link is None
    assert subtitle.series == video.series
    assert subtitle.season == video.season
    assert subtitle.episode == video.episode
    assert subtitle.format == 'HDTV'


@pytest.mark.integration
@vcr.use_cassette
def test_query_parsing_colon(episodes):
    video = episodes['csi_cyber_s02e03']
    with ItaSAProvider(test_user, test_password) as provider:
        provider.initialize()
        subtitles = provider.query(video.series, video.season, video.episode, video.format, video.resolution)
    subtitle = subtitles[0]
    assert subtitle.language == Language('ita')
    assert subtitle.page_link is None
    assert subtitle.series == video.series
    assert subtitle.season == video.season
    assert subtitle.episode == video.episode
    assert subtitle.format == 'HDTV'


@pytest.mark.integration
@vcr.use_cassette
def test_query_year(episodes):
    video = episodes['dallas_2012_s01e03']
    with ItaSAProvider(test_user, test_password) as provider:
        provider.initialize()
        subtitles = provider.query(video.series, video.season, video.episode, video.format, video.resolution)
    assert len(subtitles) == 1
    subtitle = subtitles[0]
    assert subtitle.series == video.series
    assert subtitle.season == video.season
    assert subtitle.episode == video.episode
    assert subtitle.format is None


@pytest.mark.integration
@vcr.use_cassette
def test_query_no_year(episodes):
    video = episodes['dallas_s01e03']
    with ItaSAProvider(test_user, test_password) as provider:
        provider.initialize()
        subtitles = provider.query(video.series, video.season, video.episode, video.format, video.resolution)
    assert len(subtitles) == 1
    subtitle = subtitles[0]
    assert subtitle.series == video.series
    assert subtitle.season == video.season
    assert subtitle.episode == video.episode
    assert subtitle.format is None


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles(episodes):
    video = episodes['bbt_s07e05']
    languages = {Language('ita')}
    expected_subtitles = {45282}
    with ItaSAProvider(test_user, test_password) as provider:
        provider.initialize()
        subtitles = provider.query(video.series, video.season, video.episode, video.format, video.resolution)
    assert {subtitle.sub_id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_find_subtitle_season():
    video = Episode(os.path.join('Breaking Bad', 'Season 04', 'S04E13 - Face Off.mp4'),
                    'Breaking Bad', 4, 13, title='Face Off', year=2008, tvdb_id=4164050,
                    series_tvdb_id=81189, series_imdb_id='tt0903747', format='BluRay', release_group='SPARROW',
                    resolution='720p', video_codec='h264', audio_codec='AC3', imdb_id='tt1683088', size=503587153)
    languages = {Language('ita')}
    with ItaSAProvider(test_user, test_password) as provider:
        provider.initialize()
        subtitles = provider.list_subtitles(video, languages)

    assert {subtitle.language for subtitle in subtitles} == languages
    assert {subtitle.sub_id for subtitle in subtitles} == {34442}


@pytest.mark.integration
@vcr.use_cassette
def test_find_subtitle_neither_season():
    video = Episode(os.path.join('Breaking Bad', 'Season 04', 'S04E13 - Face Off.mp4'),
                    'Breaking Bad', 4, 13, title='Face Off', year=2008, tvdb_id=4164050,
                    series_tvdb_id=81189, series_imdb_id='tt0903747', format='UHD', release_group='SPARROW',
                    resolution='720p', video_codec='h264', audio_codec='AC3', imdb_id='tt1683088', size=503587153)
    languages = {Language('ita')}
    with ItaSAProvider(test_user, test_password) as provider:
        provider.initialize()
        subtitles = provider.list_subtitles(video, languages)

    assert {subtitle.language for subtitle in subtitles} == set()
    assert {subtitle.sub_id for subtitle in subtitles} == set()


@pytest.mark.integration
@vcr.use_cassette
def test_find_subtitle_full_season():

    video = Episode(os.path.join('Person of Interest', 'Season 03', 'S03E18 - Allegiance.mkv'),
                    'Person of Interest', 3, 18, title='Allegiance', year=2011, tvdb_id=4778372,
                    series_tvdb_id=248742, series_imdb_id='tt1839578', format='BluRay', release_group='DEMAND',
                    resolution=None, video_codec='h264', audio_codec='AAC', imdb_id='tt3526628', size=256363868)
    languages = {Language('ita')}
    with ItaSAProvider(test_user, test_password) as provider:
        provider.initialize()
        subtitles = provider.list_subtitles(video, languages)

    assert len(subtitles) == 23
    assert {subtitle.language for subtitle in subtitles} == {Language('ita')}
    for subtitle in subtitles:
        if subtitle.episode == 18:
            assert subtitle.get_matches(video) == set({'series_tvdb_id', 'series', 'year', 'season', 'format',
                                                       'episode'})
        else:
            assert subtitle.get_matches(video) == set({'series_tvdb_id', 'series', 'year', 'season', 'format'})
