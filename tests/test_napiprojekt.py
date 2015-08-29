# -*- coding: utf-8 -*-
import os

from babelfish import Language
import pytest
from vcr import VCR

from subliminal.providers.napiprojekt import NapiProjektProvider, NapiProjektSubtitle


vcr = VCR(path_transformer=lambda path: path + '.yaml',
          record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
          cassette_library_dir=os.path.join('tests', 'cassettes', 'napiprojekt'))


def test_get_matches(movies):
    subtitle = NapiProjektSubtitle(Language('pol'), 'de2e9caa58dd53a6ab9d241e6b252e35')
    matches = subtitle.get_matches(movies['man_of_steel'])
    assert matches == {'hash', 'hearing_impaired'}


def test_get_matches_no_match(episodes):
    subtitle = NapiProjektSubtitle(Language('pol'), 'de2e9caa58dd53a6ab9d241e6b251234')
    matches = subtitle.get_matches(episodes['got_s03e10'], hearing_impaired=True)
    assert matches == set()


@pytest.mark.integration
@vcr.use_cassette
def test_query(movies):
    language = Language('pol')
    video = movies['man_of_steel']
    with NapiProjektProvider() as provider:
        subtitle = provider.query(language, video.hashes['napiprojekt'])
    assert subtitle.language == language
    assert subtitle.content is not None


@pytest.mark.integration
@vcr.use_cassette
def test_query_wrong_hash():
    with NapiProjektProvider() as provider:
        subtitle = provider.query(Language('pol'), 'abcdabdcabcd1234abcd1234abcd123')
    assert subtitle is None


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles(episodes):
    video = episodes['bbt_s07e05']
    languages = {Language('pol')}
    with NapiProjektProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert len(subtitles) == 1
    assert {subtitle.language for subtitle in subtitles} == languages
    assert subtitles[0].content is not None
