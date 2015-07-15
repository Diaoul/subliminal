# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

from babelfish import Language, language_converters
import pytest
from vcr import VCR

from subliminal.exceptions import AuthenticationError, ConfigurationError
from subliminal.providers.addic7ed import Addic7edProvider, Addic7edSubtitle


vcr = VCR(path_transformer=lambda path: path + '.yaml',
          match_on=['method', 'scheme', 'host', 'port', 'path', 'query', 'body'],
          cassette_library_dir=os.path.join('tests', 'cassettes', 'addic7ed'))


@pytest.mark.converter
def test_converter_convert_alpha3_country_script():
    assert language_converters['addic7ed'].convert('srp', None, 'Cyrl') == 'Serbian (Cyrillic)'


@pytest.mark.converter
def test_converter_convert_alpha3_country():
    assert language_converters['addic7ed'].convert('por', 'BR') == 'Portuguese (Brazilian)'


@pytest.mark.converter
def test_converter_convert_alpha3():
    assert language_converters['addic7ed'].convert('eus') == 'Euskera'


@pytest.mark.converter
def test_converter_convert_alpha3_name_converter():
    assert language_converters['addic7ed'].convert('fra') == 'French'


@pytest.mark.converter
def test_converter_reverse():
    assert language_converters['addic7ed'].reverse('Chinese (Traditional)') == ('zho',)


@pytest.mark.converter
def test_converter_reverse_name_converter():
    assert language_converters['addic7ed'].reverse('English') == ('eng', None, None)


def test_get_matches_with_release_group(episodes):
    subtitle = Addic7edSubtitle(Language('eng'), True, None, 'The Big Bang Theory', 7, 5, 'The Workplace Proximity',
                                2007, 'DIMENSION', None)
    matches = subtitle.get_matches(episodes['bbt_s07e05'])
    assert matches == {'series', 'season', 'episode', 'title', 'year', 'release_group'}


def test_get_matches_with_resolution_and_release_group(episodes):
    subtitle = Addic7edSubtitle(Language('heb'), True, None, 'The Big Bang Theory', 7, 5, 'The Workplace Proximity',
                                2007, '720PDIMENSION', None)
    matches = subtitle.get_matches(episodes['bbt_s07e05'])
    assert matches == {'series', 'season', 'episode', 'title', 'year', 'release_group', 'resolution'}


def test_get_matches_with_format_and_release_group(episodes):
    subtitle = Addic7edSubtitle(Language('eng'), True, None, 'Game of Thrones', 3, 10, 'Mhysa', None, 'WEB-DL-NTb',
                                None)
    matches = subtitle.get_matches(episodes['got_s03e10'])
    assert matches == {'series', 'season', 'episode', 'title', 'year', 'release_group', 'format'}


def test_get_matches_no_match(episodes):
    subtitle = Addic7edSubtitle(Language('eng'), True, None, 'The Big Bang Theory', 7, 5, 'The Workplace Proximity',
                                2007, 'DIMENSION', None)
    matches = subtitle.get_matches(episodes['got_s03e10'])
    assert matches == set()


def test_configuration_error_no_username():
    with pytest.raises(ConfigurationError):
        Addic7edProvider(password='subliminal')


def test_configuration_error_no_password():
    with pytest.raises(ConfigurationError):
        Addic7edProvider(username='subliminal')


@pytest.mark.integration
@vcr.use_cassette
def test_login():
    provider = Addic7edProvider('subliminal', 'subliminal')
    assert provider.logged_in is False
    provider.initialize()
    assert provider.logged_in is True
    r = provider.session.get(provider.server_url + 'panel.php', allow_redirects=False)
    assert r.status_code == 200


@pytest.mark.integration
@vcr.use_cassette
def test_login_bad_password():
    provider = Addic7edProvider('subliminal', 'lanimilbus')
    with pytest.raises(AuthenticationError):
        provider.initialize()


@pytest.mark.integration
@vcr.use_cassette
def test_logout():
    provider = Addic7edProvider('subliminal', 'subliminal')
    provider.initialize()
    provider.terminate()
    assert provider.logged_in is False
    r = provider.session.get(provider.server_url + 'panel.php', allow_redirects=False)
    assert r.status_code == 302


@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id():
    with Addic7edProvider() as provider:
        show_id = provider._search_show_id('The Big Bang Theory')
    assert show_id == 126


@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id_incomplete():
    with Addic7edProvider() as provider:
        show_id = provider._search_show_id('The Big Bang')
    assert show_id is None


@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id_no_year():
    with Addic7edProvider() as provider:
        show_id = provider._search_show_id('Dallas')
    assert show_id == 802


@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id_year():
    with Addic7edProvider() as provider:
        show_id = provider._search_show_id('Dallas', 2012)
    assert show_id == 2559


@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id_error():
    with Addic7edProvider() as provider:
        show_id = provider._search_show_id('The Big How I Met Your Mother')
    assert show_id is None


@pytest.mark.integration
@vcr.use_cassette('test_get_show_ids')
def test_get_show_ids():
    with Addic7edProvider() as provider:
        show_ids = provider._get_show_ids()
    assert 'the big bang theory' in show_ids
    assert show_ids['the big bang theory'] == 126


@pytest.mark.integration
@vcr.use_cassette('test_get_show_ids')
def test_get_show_ids_no_year():
    with Addic7edProvider() as provider:
        show_ids = provider._get_show_ids()
    assert 'dallas' in show_ids
    assert show_ids['dallas'] == 802


@pytest.mark.integration
@vcr.use_cassette('test_get_show_ids')
def test_get_show_ids_year():
    with Addic7edProvider() as provider:
        show_ids = provider._get_show_ids()
    assert 'dallas (2012)' in show_ids
    assert show_ids['dallas (2012)'] == 2559


@pytest.mark.integration
@vcr.use_cassette('test_get_show_ids')
def test_get_show_ids_country():
    with Addic7edProvider() as provider:
        show_ids = provider._get_show_ids()
    assert 'being human (us)' in show_ids
    assert show_ids['being human (us)'] == 1317


@pytest.mark.integration
@vcr.use_cassette('test_get_show_ids')
def test_get_show_ids_quoted():
    with Addic7edProvider() as provider:
        show_ids = provider._get_show_ids()
    assert 'marvels agents of s.h.i.e.l.d.' in show_ids
    assert show_ids['marvels agents of s.h.i.e.l.d.'] == 4010


@pytest.mark.integration
@vcr.use_cassette
def test_get_show_id_with_quotes_and_mixed_case():
    with Addic7edProvider() as provider:
        show_id = provider.get_show_id('Marvel\'s Agents of S.H.I.E.L.D.')
    assert show_id == 4010


@pytest.mark.integration
@vcr.use_cassette
def test_get_show_id_with_country():
    with Addic7edProvider() as provider:
        show_id = provider.get_show_id('Being Human', country_code='US')
    assert show_id == 1317


@pytest.mark.integration
@vcr.use_cassette
def test_get_show_id_with_year():
    with Addic7edProvider() as provider:
        show_id = provider.get_show_id('Dallas', year=2012)
    assert show_id == 2559


@pytest.mark.integration
@vcr.use_cassette
def test_get_show_id():
    with Addic7edProvider() as provider:
        show_id = provider.get_show_id('Dallas')
    assert show_id == 802


@pytest.mark.integration
@vcr.use_cassette
def test_query(episodes):
    video = episodes['bbt_s07e05']
    with Addic7edProvider() as provider:
        subtitles = provider.query(video.series, video.season, video.year)
    assert len(subtitles) == 474
    for subtitle in subtitles:
        assert subtitle.series == video.series
        assert subtitle.season == video.season
        assert subtitle.year is None


@pytest.mark.integration
@vcr.use_cassette
def test_query_wrong_series(episodes):
    video = episodes['bbt_s07e05']
    with Addic7edProvider() as provider:
        subtitles = provider.query(video.series[:12], video.season, video.year)
    assert len(subtitles) == 0


@pytest.mark.integration
@vcr.use_cassette
def test_query_parsing(episodes):
    video = episodes['got_s03e10']
    with Addic7edProvider() as provider:
        subtitles = provider.query(video.series, video.season)
    subtitle = [s for s in subtitles if s.download_link == 'updated/1/76311/1'][0]
    assert subtitle.language == Language('eng')
    assert subtitle.hearing_impaired is True
    assert subtitle.page_link == 'http://www.addic7ed.com/serie/Game_of_Thrones/3/10/Mhysa'
    assert subtitle.series == video.series
    assert subtitle.season == video.season
    assert subtitle.episode == video.episode
    assert subtitle.title == video.title
    assert subtitle.year == video.year
    assert subtitle.version == 'EVOLVE'


@pytest.mark.integration
@vcr.use_cassette
def test_query_year(episodes):
    video = episodes['dallas_2012_s01e03']
    with Addic7edProvider() as provider:
        subtitles = provider.query(video.series, video.season, video.year)
    assert len(subtitles) == 123
    for subtitle in subtitles:
        assert subtitle.series == video.series
        assert subtitle.season == video.season
        assert subtitle.year == video.year


@pytest.mark.integration
@vcr.use_cassette
def test_query_no_year(episodes):
    video = episodes['dallas_s01e03']
    with Addic7edProvider() as provider:
        subtitles = provider.query(video.series, video.season)
    assert len(subtitles) == 7
    for subtitle in subtitles:
        assert subtitle.series == video.series
        assert subtitle.season == video.season
        assert subtitle.year == video.year


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles(episodes):
    video = episodes['bbt_s07e05']
    languages = {Language('deu'), Language('fra')}
    expected_subtitles = {'updated/8/80254/1', 'updated/11/80254/5'}
    with Addic7edProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert {subtitle.download_link for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle(episodes):
    video = episodes['bbt_s07e05']
    languages = {Language('fra')}
    with Addic7edProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        provider.download_subtitle(subtitles[0])
    assert subtitles[0].content is not None
    assert subtitles[0].is_valid() is True
