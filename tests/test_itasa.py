# -*- coding: utf-8 -*-
import os

from babelfish import Language
import pytest
from vcr import VCR

from subliminal.exceptions import AuthenticationError, ConfigurationError
from subliminal.providers.itasa import ItaSAProvider, ItaSASubtitle


vcr = VCR(path_transformer=lambda path: path + '.yaml',
          record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
          match_on=['method', 'scheme', 'host', 'port', 'path', 'query', 'body'],
          cassette_library_dir=os.path.join('tests', 'cassettes', 'itasa'))
test_user = 'subliminal-test'
test_password = 'subliminal-test'


def test_get_matches_season_episode_resolution(episodes):
    subtitle = ItaSASubtitle(5514, 'The Big Bang Theory', 7, 5, '720p',
                             'The.Big.Bang.Theory.s07e05.720p.sub.itasa.srt')
    matches = subtitle.get_matches(episodes['bbt_s07e05'])
    assert matches == {'series', 'season', 'episode', 'resolution'}


def test_get_matches_season_episode(episodes):
    subtitle = ItaSASubtitle(5514, 'The Big Bang Theory', 7, 5, 'HDTV',
                             'The.Big.Bang.Theory.s07e05.sub.itasa.srt')
    matches = subtitle.get_matches(episodes['bbt_s07e05'])
    assert matches == {'series', 'season', 'episode', 'format'}


def test_get_matches_no_match(episodes):
    subtitle = ItaSASubtitle(5514, 'The Big Bang Theory', 7, 5, 'HDTV',
                             'The.Big.Bang.Theory.s07e05.sub.itasa.srt')
    matches = subtitle.get_matches(episodes['got_s03e10'])
    assert matches == set([])


def test_get_matches_episode_hash(episodes):
    subtitle = ItaSASubtitle(5514, 'The Big Bang Theory', 7, 5, 'HDTV',
                             'The.Big.Bang.Theory.s07e05.sub.itasa.srt', '6303e7ee6a835e9fcede9fb2fb00cb36')
    matches = subtitle.get_matches(episodes['bbt_s07e05'])
    assert matches == set(['episode', 'format', 'season', 'series', 'hash'])


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
        subtitles = provider.query(video.series, video.season, video.episode, video.format)
    assert len(subtitles) == 1
    for subtitle in subtitles:
        assert subtitle.series == video.series
        assert subtitle.season == video.season
        assert subtitle.episode == video.episode
        assert subtitle.format == video.format
        assert len(subtitle.content) == 28424


@pytest.mark.integration
@vcr.use_cassette
def test_query_wrong_series(episodes):
    video = episodes['bbt_s07e05']
    with ItaSAProvider(test_user, test_password) as provider:
        provider.initialize()
        subtitles = provider.query(video.series[:12], video.season, video.episode, video.format)
    assert len(subtitles) == 0


@pytest.mark.integration
@vcr.use_cassette
def test_query_parsing(episodes):
    video = episodes['got_s03e10']
    with ItaSAProvider(test_user, test_password) as provider:
        provider.initialize()
        subtitles = provider.query(video.series, video.season, video.episode, video.format)
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
        subtitles = provider.query(video.series, video.season, video.episode, video.format)
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
        subtitles = provider.query(video.series, video.season, video.episode, video.format)
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
        subtitles = provider.query(video.series, video.season, video.episode, video.format)
        print
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
        subtitles = provider.query(video.series, video.season, video.episode, video.format)
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
    expected_subtitles = {45280}
    with ItaSAProvider(test_user, test_password) as provider:
        provider.initialize()
        subtitles = provider.query(video.series, video.season, video.episode, video.format)
    assert {subtitle.sub_id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages
