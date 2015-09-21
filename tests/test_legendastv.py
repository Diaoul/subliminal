# -*- coding: utf-8 -*-
import os

from babelfish import Language, language_converters
import pytest
from vcr import VCR
from subliminal.exceptions import ConfigurationError, AuthenticationError
from subliminal.providers.legendastv import LegendasTvSubtitle, LegendasTvProvider

USERNAME = 'subliminal'
PASSWORD = 'subliminal'

vcr = VCR(path_transformer=lambda path: path + '.yaml',
          record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
          match_on=['method', 'scheme', 'host', 'port', 'path', 'query', 'body'],
          cassette_library_dir=os.path.join('tests', 'cassettes', 'legendastv'))


@pytest.mark.converter
def test_converter_convert_alpha3_country():
    assert language_converters['legendastv'].convert('por', 'BR') == 1


@pytest.mark.converter
def test_converter_convert_alpha3():
    assert language_converters['legendastv'].convert('eng') == 2


@pytest.mark.converter
def test_converter_convert_unsupported_alpha3():
    with pytest.raises(ConfigurationError):
        language_converters['legendastv'].convert('rus')


@pytest.mark.converter
def test_converter_reverse():
    assert language_converters['legendastv'].reverse(10) == ('por',)


@pytest.mark.converter
def test_converter_reverse_name_converter():
    assert language_converters['legendastv'].reverse(3) == ('spa',)


@pytest.mark.converter
def test_converter_reverse_unsupported_language_number():
    with pytest.raises(ConfigurationError):
        language_converters['legendastv'].reverse(20)


def test_get_matches_with_format_and_video_codec(episodes):
    subtitle = LegendasTvSubtitle(Language('por', 'BR'), None, '5261e6de679eb',
                                  'The.Big.Bang.Theory.S07E05.HDTV.x264-LOL-AFG-DIMENSION', type='episode', season=7,
                                  no_downloads=50073, rating=10, featured=True, multiple_episodes=False)

    matches = subtitle.get_matches(episodes['bbt_s07e05'])
    assert matches == {'series', 'season', 'episode', 'video_codec', 'format', 'hearing_impaired'}


@pytest.mark.integration
@vcr.use_cassette
def test_login():
    provider = LegendasTvProvider(USERNAME, PASSWORD)
    assert provider.logged_in is False
    provider.initialize()
    assert provider.logged_in is True


@pytest.mark.integration
@vcr.use_cassette
def test_login_bad_password():
    provider = LegendasTvProvider(USERNAME, 'wrong')
    with pytest.raises(AuthenticationError):
        provider.initialize()


@pytest.mark.integration
@vcr.use_cassette
def test_logout():
    provider = LegendasTvProvider(USERNAME, PASSWORD)
    provider.initialize()
    provider.terminate()
    assert provider.logged_in is False


@pytest.mark.integration
@vcr.use_cassette
def test_search_titles_with_series():
    with LegendasTvProvider() as provider:
        titles = provider.search_titles(None, 'The Big Bang Theory', 7, None)
    assert titles
    assert len(titles) == 1
    assert titles[0].get('id') == '30730'


@pytest.mark.integration
@vcr.use_cassette
def test_search_titles_with_series_without_season():
    with LegendasTvProvider() as provider:
        titles = provider.search_titles(None, 'The Big Bang Theory', None, None)
    assert not titles


@pytest.mark.integration
@vcr.use_cassette
def test_search_titles_with_movies():
    with LegendasTvProvider() as provider:
        titles = provider.search_titles('Man of Steel', None, None, 2013)
    assert titles
    assert len(titles) == 1
    assert titles[0].get('id') == '29087'


@pytest.mark.integration
@vcr.use_cassette
def test_search_titles_with_movies_without_year():
    with LegendasTvProvider() as provider:
        titles = provider.search_titles('Man of steel', None, None, None)
    assert titles
    assert len(titles) == 1
    assert titles[0].get('id') == '29087'


@pytest.mark.integration
@vcr.use_cassette
def test_search_titles_with_movies_without_year_and_partial_name():
    with LegendasTvProvider() as provider:
        titles = provider.search_titles('Man of Ste', None, None, None)
    assert not titles


@pytest.mark.integration
@vcr.use_cassette
def test_query_movie(movies):
    video = movies['man_of_steel']
    language = Language('por', 'BR')
    expected_subtitles = {
        '54edd551e869a',
        '5262e21d58bab',
        '525e738d4866b',
        '0240fcbcb3a8918cbd993a7457720508',
        'a50ef54a73c490f3d7f63c333f5d3e07',
        '525dd8547cb72',
        '527a1eda17867',
        '525d86f6c6560',
        '5285f5daac692',
        '526076d4af488',
        '52cc3e195127e',
        '5356d2eed7622',
        '527d55c0c02bc',
        '52604f2d2099a',
        'cab70863ae461c10ab404e36c807d65a'
    }

    with LegendasTvProvider() as provider:
        subtitles = provider.query(language, video, movie=video.title, year=video.year)

    assert {subtitle.subtitle_id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == {language}


@pytest.mark.integration
@vcr.use_cassette
def test_query_episode(episodes):
    video = episodes['bbt_s07e05']
    language = Language('por', 'BR')
    expected_subtitles = {
        '5261e6de679eb',
        '537a74584945b',
        '5380d44e2beb1',
        '5388d59bd7671',
        '5260ff24907e4',
        '5266aecaead61',
        '5339b32f236c7',
        '5391017f64b99',
        '54bd9555c43aa',
        '5387da135c96f',
        '5376e044d892e',
        '5388d55b22707',
        '5376e0128cfe6',
        '5387d9cfc5fff'
    }

    # This subtitle is not expected. It's marked wrongly as 'pack'. It's a different episode number
    # <LegendasTvSubtitle u'52f6ed91971a0: The.Big.Bang.Theory.S07E15.720p.HDTV.X264-DIMENSION' [pt-BR]>

    with LegendasTvProvider() as provider:
        subtitles = provider.query(language, video, series=video.series, season=video.season, episode=video.episode)

    assert {subtitle.subtitle_id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == {language}


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_movie(movies):
    video = movies['man_of_steel']
    languages = {Language('por', 'BR'), Language('eng')}
    expected_subtitles = {
        '54edd551e869a',
        '5262e21d58bab',
        '525e738d4866b',
        '0240fcbcb3a8918cbd993a7457720508',
        'a50ef54a73c490f3d7f63c333f5d3e07',
        '525dd8547cb72',
        '527a1eda17867',
        '525d86f6c6560',
        '5285f5daac692',
        '526076d4af488',
        '52cc3e195127e',
        '5356d2eed7622',
        '527d55c0c02bc',
        '52604f2d2099a',
        'cab70863ae461c10ab404e36c807d65a',
        '525d8c2444851'
    }

    with LegendasTvProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)

    assert {subtitle.subtitle_id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_episode(episodes):
    video = episodes['got_s03e10']
    languages = {Language('por', 'BR')}
    expected_subtitles = {
        '55ea0ba5f54be723d3f834e426bf0204',
        '52e4ea1c8ba43',
        '10308877e71f0588467a1ac46cd08a81',
        '53b37f580d814',
        '52e98a71044ce',
        '5443056cb0148',
        'ce9c25ba16ea2f59f659defccea873f6',
        '52d297a171971',
        '530f8737c42eb',
        'bbaeda55c45bfe9da2b34a196434521e',
        '8b567ce2eb0852950f98ef99f6e7975c',
        '998c246f63f8621c96cb97fafc491b1a',
        '545ffd1a370f9'
    }

    with LegendasTvProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert {subtitle.subtitle_id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle(movies):
    video = movies['man_of_steel']
    languages = {Language('por', 'BR'), Language('eng')}

    with LegendasTvProvider(USERNAME, PASSWORD) as provider:
        provider.initialize()
        subtitles = provider.list_subtitles(video, languages)
        subtitle = [s for s in subtitles if s.subtitle_id == '525e738d4866b'][0]
        provider.download_subtitle(subtitle)
        provider.terminate()

    assert subtitle.content is not None
    assert subtitle.is_valid() is True
