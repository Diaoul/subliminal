# -*- coding: utf-8 -*-
import os

from babelfish import Language
import pytest
from vcr import VCR

from subliminal.providers.thesubdb import TheSubDBProvider, TheSubDBSubtitle


vcr = VCR(path_transformer=lambda path: path + '.yaml',
          record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
          cassette_library_dir=os.path.join('tests', 'cassettes', 'thesubdb'))


def test_get_matches(movies):
    subtitle = TheSubDBSubtitle(Language('eng'), 'ad32876133355929d814457537e12dc2')
    matches = subtitle.get_matches(movies['man_of_steel'])
    assert matches == {'hash', 'hearing_impaired'}


def test_get_matches_no_match(episodes):
    subtitle = TheSubDBSubtitle(Language('eng'), 'ad32876133355929d814457537e12dc2')
    matches = subtitle.get_matches(episodes['got_s03e10'], hearing_impaired=True)
    assert matches == set()


@pytest.mark.integration
@vcr.use_cassette
def test_query(movies):
    video = movies['man_of_steel']
    expected_languages = {Language('eng'), Language('por')}
    with TheSubDBProvider() as provider:
        subtitles = provider.query(video.hashes['thesubdb'])
    assert len(subtitles) == 2
    assert {subtitle.language for subtitle in subtitles} == expected_languages


@pytest.mark.integration
@vcr.use_cassette
def test_query_wrong_hash():
    with TheSubDBProvider() as provider:
        subtitles = provider.query('11223344556677899877665544332211')
    assert len(subtitles) == 0


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles(episodes):
    video = episodes['bbt_s07e05']
    languages = {Language('eng'), Language('fra')}
    with TheSubDBProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert len(subtitles) == 2
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle(episodes):
    video = episodes['bbt_s07e05']
    languages = {Language('eng'), Language('fra')}
    with TheSubDBProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        provider.download_subtitle(subtitles[0])
    assert subtitles[0].content is not None
    assert subtitles[0].is_valid() is True
