# -*- coding: utf-8 -*-
import os

from babelfish import Language, language_converters
import pytest
from vcr import VCR

from subliminal.providers.tvsubtitles import TVsubtitlesProvider, TVsubtitlesSubtitle


vcr = VCR(path_transformer=lambda path: path + '.yaml',
          record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
          match_on=['method', 'scheme', 'host', 'port', 'path', 'query', 'body'],
          cassette_library_dir=os.path.realpath(os.path.realpath(os.path.join('tests', 'cassettes', 'tvsubtitles'))))


@pytest.mark.converter
def test_converter_convert_alpha3_country():
    assert language_converters['tvsubtitles'].convert('por', 'BR') == 'br'


@pytest.mark.converter
def test_converter_convert_alpha3():
    assert language_converters['tvsubtitles'].convert('ukr') == 'ua'


@pytest.mark.converter
def test_converter_convert_alpha3_alpha2_converter():
    assert language_converters['tvsubtitles'].convert('fra') == 'fr'


@pytest.mark.converter
def test_converter_reverse():
    assert language_converters['tvsubtitles'].reverse('gr') == ('ell',)


@pytest.mark.converter
def test_converter_reverse_name_converter():
    assert language_converters['tvsubtitles'].reverse('en') == ('eng', None, None)


def test_get_matches_format_release_group(episodes):
    subtitle = TVsubtitlesSubtitle(Language('fra'), None, 249518, 'The Big Bang Theory', 7, 5, 2007, 'HDTV',
                                   'lol-dimension')
    matches = subtitle.get_matches(episodes['bbt_s07e05'])
    assert matches == {'series', 'season', 'episode', 'year', 'format', 'release_group'}


def test_get_matches_format_equivalent_release_group(episodes):
    subtitle = TVsubtitlesSubtitle(Language('fra'), None, 249518, 'The Big Bang Theory', 7, 5, 2007, 'HDTV',
                                   'lol')
    matches = subtitle.get_matches(episodes['bbt_s07e05'])
    assert matches == {'series', 'season', 'episode', 'year', 'format', 'release_group'}


def test_get_matches_video_codec_resolution(episodes):
    subtitle = TVsubtitlesSubtitle(Language('por'), None, 261077, 'Game of Thrones', 3, 10, None, '720p.BluRay',
                                   'x264-DEMAND')
    matches = subtitle.get_matches(episodes['got_s03e10'])
    assert matches == {'series', 'season', 'episode', 'year', 'video_codec', 'resolution'}


def test_get_matches_no_match(episodes):
    subtitle = TVsubtitlesSubtitle(Language('por'), None, 261077, 'Game of Thrones', 3, 10, 2011, '1080p.BluRay',
                                   'DEMAND')
    matches = subtitle.get_matches(episodes['bbt_s07e05'])
    assert matches == set()


@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id():
    with TVsubtitlesProvider() as provider:
        show_id = provider.search_show_id('The Big Bang Theory')
    assert show_id == 154


@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id_incomplete():
    with TVsubtitlesProvider() as provider:
        show_id = provider.search_show_id('The Big Bang')
    assert show_id is None


@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id_ambiguous():
    with TVsubtitlesProvider() as provider:
        show_id = provider.search_show_id('New Girl')
    assert show_id == 977


@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id_us():
    with TVsubtitlesProvider() as provider:
        show_id = provider.search_show_id('House of Cards', 2013)
    assert show_id == 1246


@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id_uk():
    with TVsubtitlesProvider() as provider:
        show_id = provider.search_show_id('Beautiful People')
    assert show_id == 657


@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id_no_year():
    with TVsubtitlesProvider() as provider:
        show_id = provider.search_show_id('Dallas')
    assert show_id == 646


@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id_year_in_title():
    with TVsubtitlesProvider() as provider:
        show_id = provider.search_show_id('Dallas', 2012)
    assert show_id == 1127


@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id_error():
    with TVsubtitlesProvider() as provider:
        show_id = provider.search_show_id('The Big How I Met Your Mother')
    assert show_id is None


@pytest.mark.integration
@vcr.use_cassette
def test_get_episode_ids():
    expected_episode_ids = {1: 34274, 2: 34275, 3: 34276, 4: 34277, 5: 34849, 6: 34923, 7: 35022, 8: 35023, 9: 35436,
                            10: 35503, 11: 35887, 12: 36369, 13: 36513, 14: 36610, 15: 36718, 16: 36795, 17: 37152,
                            18: 37153, 19: 37407, 20: 37863, 21: 38218, 22: 38574, 23: 38686, 24: 38687}
    with TVsubtitlesProvider() as provider:
        episode_ids = provider.get_episode_ids(154, 5)
    assert episode_ids == expected_episode_ids


@pytest.mark.integration
@vcr.use_cassette
def test_get_episode_ids_wrong_season():
    with TVsubtitlesProvider() as provider:
        episode_ids = provider.get_episode_ids(154, 55)
    assert len(episode_ids) == 0


@pytest.mark.integration
@vcr.use_cassette
def test_query(episodes):
    video = episodes['bbt_s07e05']
    expected_subtitles = {268673, 249733, 249518, 249519, 249714, 32596, 249590, 249592, 249499, 261214}
    with TVsubtitlesProvider() as provider:
        show_id = provider.search_show_id(video.series, video.year)
        subtitles = provider.query(show_id, video.series, video.season, video.episode, video.year)
    assert {subtitle.subtitle_id for subtitle in subtitles} == expected_subtitles


@pytest.mark.integration
@vcr.use_cassette
def test_query_no_year(episodes):
    video = episodes['dallas_s01e03']
    expected_subtitles = {124753}
    with TVsubtitlesProvider() as provider:
        show_id = provider.search_show_id(video.series, video.year)
        subtitles = provider.query(show_id, video.series, video.season, video.episode, video.year)
    assert {subtitle.subtitle_id for subtitle in subtitles} == expected_subtitles


@pytest.mark.integration
@vcr.use_cassette
def test_query_wrong_series(episodes):
    video = episodes['bbt_s07e05']
    with TVsubtitlesProvider() as provider:
        subtitles = provider.query(155, video.series[:12], video.season, video.episode, video.year)
    assert len(subtitles) == 0


@pytest.mark.integration
@vcr.use_cassette
def test_query_wrong_episode(episodes):
    video = episodes['bbt_s07e05']
    with TVsubtitlesProvider() as provider:
        show_id = provider.search_show_id(video.series, video.year)
        subtitles = provider.query(show_id, video.series, video.season, 55, video.year)
    assert len(subtitles) == 0


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles(episodes):
    video = episodes['bbt_s07e05']
    languages = {Language('eng'), Language('fra')}
    expected_subtitles = {249592, 249499, 32596, 249518}
    with TVsubtitlesProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert {subtitle.subtitle_id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages
    assert subtitles[0].release == 'The Big Bang Theory 7x05 (HDTV.LOL)'


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle(episodes):
    video = episodes['bbt_s07e05']
    languages = {Language('eng'), Language('fra')}
    with TVsubtitlesProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        provider.download_subtitle(subtitles[0])
    assert subtitles[0].content is not None
    assert subtitles[0].is_valid() is True


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_episode_alternative_series(episodes):
    video = episodes['turn_s03e01']
    languages = {Language('fra')}
    expected_subtitles = {307588}
    with TVsubtitlesProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert {subtitle.subtitle_id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages
