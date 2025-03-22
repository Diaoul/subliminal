import os

import pytest
from babelfish import Language  # type: ignore[import-untyped]
from vcr import VCR  # type: ignore[import-untyped]

from subliminal.providers.napiprojekt import NapiProjektProvider, NapiProjektSubtitle
from subliminal.video import Episode, Movie

vcr = VCR(
    path_transformer=lambda path: path + '.yaml',
    record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
    decode_compressed_response=True,
    cassette_library_dir=os.path.realpath(os.path.join('tests', 'cassettes', 'napiprojekt')),
)


def test_hash_napiprojekt(mkv: dict[str, str]) -> None:
    assert NapiProjektProvider.hash_video(mkv['test1']) == '9884a2b66dcb2965d0f45ce84e37b60c'


def test_get_matches(movies: dict[str, Movie]) -> None:
    subtitle = NapiProjektSubtitle(Language('pol'), '6303e7ee6a835e9fcede9fb2fb00cb36')
    matches = subtitle.get_matches(movies['man_of_steel'])
    assert matches == {'hash'}


def test_get_matches_no_match(episodes: dict[str, Episode]) -> None:
    subtitle = NapiProjektSubtitle(Language('pol'), 'de2e9caa58dd53a6ab9d241e6b251234')
    matches = subtitle.get_matches(episodes['got_s03e10'])
    assert matches == set()


@pytest.mark.integration
@vcr.use_cassette
def test_query_microdvd(movies: dict[str, Movie]) -> None:
    language = Language('pol')
    video = movies['man_of_steel']
    with NapiProjektProvider() as provider:
        subtitles = provider.query(language, video.hashes['napiprojekt'])
    assert len(subtitles) == 1
    subtitle = subtitles[0]
    assert subtitle.language == language
    assert subtitle.content
    assert subtitle.is_valid()
    assert subtitle.subtitle_format == 'microdvd'


@pytest.mark.integration
@vcr.use_cassette
def test_query_srt(episodes: dict[str, Episode]) -> None:
    language = Language('pol')
    video = episodes['suits_s06_e12']
    with NapiProjektProvider() as provider:
        subtitles = provider.query(language, video.hashes['napiprojekt'])
    assert len(subtitles) == 1
    subtitle = subtitles[0]
    assert subtitle.language == language
    assert subtitle.content
    assert subtitle.is_valid()
    assert subtitle.subtitle_format == 'srt'


@pytest.mark.integration
@vcr.use_cassette
def test_query_srt_reencode(episodes: dict[str, Episode]) -> None:
    language = Language('pol')
    video = episodes['suits_s06_e13']
    with NapiProjektProvider() as provider:
        subtitles = provider.query(language, video.hashes['napiprojekt'])
    assert len(subtitles) == 1
    subtitle = subtitles[0]
    assert subtitle.language == language
    assert subtitle.content
    assert subtitle.is_valid()
    assert subtitle.subtitle_format == 'srt'
    assert subtitle.encoding == 'cp1250'
    subtitle.reencode()
    assert subtitle.encoding == 'utf-8'
    assert 'O czym myślisz?' in subtitle.text


@pytest.mark.integration
@vcr.use_cassette
def test_query_wrong_hash() -> None:
    with NapiProjektProvider() as provider:
        subtitles = provider.query(Language('pol'), 'abcdabdcabcd1234abcd1234abcd123')
    assert len(subtitles) == 0


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    languages = {Language('pol')}
    with NapiProjektProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert len(subtitles) == 1
    subtitle = subtitles[0]
    assert {subtitle.language} == languages
    assert subtitle.content
    assert subtitle.is_valid()


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitles(episodes: dict[str, Episode]) -> None:
    video = episodes['got_s03e10']
    languages = {Language('pol')}
    with NapiProjektProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert len(subtitles) == 1
    subtitle = subtitles[0]
    assert {subtitle.language} == languages

    content = subtitle.content
    assert content

    with NapiProjektProvider() as provider:
        provider.download_subtitle(subtitle)
    assert subtitle.content == content
    assert subtitle.is_valid()
