#  -*- coding: utf-8 -*-
import os

from babelfish import Language, language_converters
import pytest
from vcr import VCR

from subliminal.providers.hosszupuska import HosszupuskaProvider, HosszupuskaSubtitle


vcr = VCR(path_transformer=lambda path: path + '.yaml',
          record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
          match_on=['method', 'scheme', 'host', 'port', 'path', 'query', 'body'],
          cassette_library_dir=os.path.realpath(os.path.realpath(os.path.join('tests', 'cassettes', 'hosszupuska'))))


@pytest.mark.converter
def test_converter_convert_alpha3_country():
    assert language_converters['hosszupuska'].convert('hun', 'HU') == 'hu'


@pytest.mark.converter
def test_converter_convert_alpha3():
    assert language_converters['hosszupuska'].convert('eng') == 'en'


@pytest.mark.converter
def test_converter_convert_alpha3_alpha2_converter():
    assert language_converters['hosszupuska'].convert('fra') == 'fr'
#
#
# @pytest.mark.converter
# def test_converter_reverse_name_converter():
#     assert language_converters['hosszupuska'].reverse('en') == ('eng', None, None)


def test_get_matches_format_release_group(episodes):
    subtitle = HosszupuskaSubtitle(Language('hun'), None, 249518, 'The Big Bang Theory', 7, 5, 'HDTV',
                                   'lol-dimension', None, None)
    matches = subtitle.get_matches(episodes['bbt_s07e05'])
    assert matches == {'series', 'season', 'episode', 'format', 'release_group', 'year'}


def test_get_matches_format_equivalent_release_group(episodes):
    subtitle = HosszupuskaSubtitle(Language('fra'), None, 249518, 'The Big Bang Theory', 7, 5, 'HDTV',
                                   'lol', None, None)
    matches = subtitle.get_matches(episodes['bbt_s07e05'])
    assert matches == {'series', 'season', 'episode', 'format', 'release_group', 'year'}


def test_get_matches_video_codec_resolution(episodes):
    subtitle = HosszupuskaSubtitle(Language('hun'), None, 261077, 'The 100', 3, 9, 'HDTV',
                                   'rmteam', '720p', None)
    matches = subtitle.get_matches(episodes['the_100_s03e09'])
    assert matches == {'series', 'season', 'episode', 'format', 'resolution', 'year'}


def test_get_matches_no_match(episodes):
    subtitle = HosszupuskaSubtitle(Language('hun'), None, 261077, 'Game of Thrones', 3, 15, '1080p.BluRay',
                                   'DEMAND', None, None)
    matches = subtitle.get_matches(episodes['bbt_s07e05'])
    assert matches == set()


def test_print_subtitle(episodes):
    subtitle = HosszupuskaSubtitle(Language('hun'), None, 261077, 'The 100', 3, 9, 'HDTV',
                                   'rmteam', '720p', '2016')
    substr = "Subtitle id: 261077 Series: The 100 Season: 3 Episode: 9 " \
             + "Release_group: rmteam  Format: HDTV  Resolution: 720p Year: 2016"
    assert str(subtitle) == substr


def test_language(episodes):
    assert HosszupuskaProvider().get_language('1.gif') == 'hu'
    assert HosszupuskaProvider().get_language('2.gif') == 'en'
    assert HosszupuskaProvider().get_language('3.gif') is None


@pytest.mark.integration
@vcr.use_cassette
def test_query_no_year(episodes):
    video = episodes['dallas_s01e03']
    expected_subtitles = {'0036055', '0036106'}
    with HosszupuskaProvider() as provider:
        subtitles = provider.query(video.series, video.season, video.episode, video.year)
    assert {subtitle.subtitle_id for subtitle in subtitles} == expected_subtitles


@pytest.mark.integration
@vcr.use_cassette
def test_query_wrong_series(episodes):
    video = episodes['bbt_s07e05']
    with HosszupuskaProvider() as provider:
        subtitles = provider.query(video.series[:12], video.season, video.episode, video.year)
    assert len(subtitles) == 0


@pytest.mark.integration
@vcr.use_cassette
def test_query_wrong_episode(episodes):
    video = episodes['bbt_s07e05']
    with HosszupuskaProvider() as provider:
        subtitles = provider.query(video.series, video.season, 55, video.year)
    assert len(subtitles) == 0


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles(episodes):
    video = episodes['the_x_files_s10e02']
    languages = {Language('hun')}
    expected_subtitles = {'0060314', '0059143', '0059145', '0059146'}
    with HosszupuskaProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert {subtitle.subtitle_id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle(episodes):
    video = episodes['the_x_files_s10e02']
    languages = {Language('eng'), Language('hun')}
    with HosszupuskaProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        provider.download_subtitle(subtitles[0])
    assert subtitles[0].content is not None
    assert subtitles[0].is_valid() is True
