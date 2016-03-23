# -*- coding: utf-8 -*-
import os

from babelfish import Language, language_converters
import pytest
from vcr import VCR

from subliminal.providers.shooter import ShooterSubtitle, ShooterProvider


vcr = VCR(path_transformer=lambda path: path + '.yaml',
          record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
          match_on=['method', 'scheme', 'host', 'port', 'path', 'body'],
          cassette_library_dir=os.path.realpath(os.path.join('tests', 'cassettes', 'shooter')))


def test_get_matches_movie_hash(movies):
    subtitle = ShooterSubtitle(Language('zho'), '314f454ab464775498ae6f1f5ad813a9;fdaa8b702d8936feba2122e93ba5c44f;'
                               '0a6935e3436aa7db5597ef67a2c494e3;4d269733f36ddd49f71e92732a462fe5', None)
    matches = subtitle.get_matches(movies['man_of_steel'])
    assert matches == {'hash'}


@pytest.mark.converter
def test_converter_convert_alpha3():
    assert language_converters['shooter'].convert('zho') == 'chn'


@pytest.mark.converter
def test_converter_reverse():
    assert language_converters['shooter'].reverse('chn') == ('zho',)


@pytest.mark.integration
@vcr.use_cassette
def test_query_movie(movies):
    language = Language('zho')
    video = movies['man_of_steel']
    with ShooterProvider() as provider:
        subtitles = provider.query(language, video.name, video.hashes['shooter'])
    assert len(subtitles) == 3


@pytest.mark.integration
@vcr.use_cassette
def test_query_movie_no_hash(movies):
    language = Language('zho')
    video = movies['enders_game']
    with ShooterProvider() as provider:
        subtitles = provider.query(language, video.name)
    assert len(subtitles) == 0


@pytest.mark.integration
@vcr.use_cassette
def test_query_episode(episodes):
    video = episodes['bbt_s07e05']
    language = Language('zho')
    with ShooterProvider() as provider:
        subtitles = provider.query(language, video.name, video.hashes['shooter'])
    assert len(subtitles) == 3


@pytest.mark.integration
@vcr.use_cassette
def test_query_episode_no_hash(episodes):
    video = episodes['dallas_2012_s01e03']
    language = Language('zho')
    with ShooterProvider() as provider:
        subtitles = provider.query(language, video.name)
    assert len(subtitles) == 1


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles(movies):
    video = movies['man_of_steel']
    languages = {Language('eng'), Language('zho')}
    with ShooterProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert len(subtitles) == 6
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle(movies):
    video = movies['man_of_steel']
    languages = {Language('eng'), Language('zho')}
    with ShooterProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        provider.download_subtitle(subtitles[0])
    assert subtitles[0].content is not None
