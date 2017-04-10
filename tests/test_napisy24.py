# -*- coding: utf-8 -*-
import os

from babelfish import Language
import pytest
from vcr import VCR

from subliminal.providers.napisy24 import Napisy24Provider, Napisy24Subtitle

vcr = VCR(path_transformer=lambda path: path + '.yaml',
          record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
          cassette_library_dir=os.path.realpath(os.path.join('tests', 'cassettes', 'napisy24')))


def test_get_matches(movies):
    subtitle = Napisy24Subtitle(Language('pol'), '5b8f8f4e41ccb21e', 'tt0770828')
    matches = subtitle.get_matches(movies['man_of_steel'])
    assert matches == {'hash', 'imdb_id'}


def test_get_matches_no_match(episodes):
    subtitle = Napisy24Subtitle(Language('pol'), 'abcd1234abcd1234', 'tt1234567')
    matches = subtitle.get_matches(episodes['got_s03e10'])
    assert matches == set()


@pytest.mark.integration
@vcr.use_cassette
def test_query(movies):
    language = Language('pol')
    video = movies['man_of_steel']
    with Napisy24Provider() as provider:
        subtitle = provider.query(language, video.size, video.name, video.hashes['napisy24'])
    assert subtitle is not None
    assert subtitle.language == language
    assert subtitle.imdb_id == video.imdb_id
    assert subtitle.content is not None


@pytest.mark.integration
@vcr.use_cassette
def test_query_wrong_params():
    with Napisy24Provider() as provider:
        subtitle = provider.query(Language('pol'), 0, '', 'abcdabdcabcd1234abcd1234abcd123')
    assert subtitle is None


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles(movies):
    languages = {Language('pol')}
    video = movies['man_of_steel']
    with Napisy24Provider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert len(subtitles) == 1
    assert {subtitle.language for subtitle in subtitles} == languages
    assert subtitles[0].content is not None
