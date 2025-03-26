import os
from pathlib import Path

import pytest
from babelfish import Language  # type: ignore[import-untyped]
from vcr import VCR  # type: ignore[import-untyped]

from subliminal.providers.bsplayer import BSPlayerProvider, BSPlayerSubtitle
from subliminal.video import Episode, Movie

vcr = VCR(
    path_transformer=lambda path: path + '.yaml',
    record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
    decode_compressed_response=True,
    match_on=['method', 'scheme', 'host', 'port', 'path', 'query', 'body'],
    cassette_library_dir=os.path.realpath(os.path.join('tests', 'cassettes', 'bsplayer')),
)

SEARCH_URL = 'http://s1.api.bsplayer-subtitles.com/v1.php'


def test_hash_bsplayer(mkv: dict[str, str]) -> None:
    assert BSPlayerProvider.hash_video(mkv['test1']) == '40b44a7096b71ec3'


def test_hash_bsplayer_too_small(tmp_path: Path) -> None:
    path = tmp_path / 'test_too_small.mkv'
    path.touch()
    assert BSPlayerProvider.hash_video(str(path)) is None


def test_get_matches_movie_hash(episodes: dict[str, Episode]) -> None:
    subtitle = BSPlayerSubtitle(
        language=Language('spa'),
        subtitle_id='16442520',
        size=12185,
        page_link=None,
        filename='The.Big.Bang.Theory.S07E05.720p.HDTV.X264-DIMENSION.srt',
        fps=0,
        subtitle_format='srt',
        subtitle_hash='dbaf71fc665f83a716ae3f5daa62b7a0',
        rating='5',
        season=None,
        episode=None,
        encoding=None,
        imdb_id='2557490',
        imdb_rating=None,
        movie_year=None,
        movie_name=None,
        movie_hash='6878b3ef7c1bd19e',
        movie_size=0,
    )

    matches = subtitle.get_matches(episodes['bbt_s07e05'])
    assert matches == {'hash'}


@pytest.mark.integration
@vcr.use_cassette
def test_login() -> None:
    provider = BSPlayerProvider(search_url=SEARCH_URL)
    assert provider.token is None
    provider.initialize()
    assert provider.token is not None


@pytest.mark.integration
@vcr.use_cassette
def test_logout() -> None:
    provider = BSPlayerProvider(search_url=SEARCH_URL)
    provider.initialize()
    provider.terminate()
    assert provider.token is None


@pytest.mark.integration
@vcr.use_cassette
def test_query_hash_size(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    languages = {Language('spa')}
    expected_subtitles = {
        '16406078',
        '16416262',
        '16418130',
        '16443177',
        '16459402',
        '16460111',
        '16461946',
        '16471760',
        '16476519',
        '16478096',
        '16478430',
        '16479531',
        '16480125',
        '16511626',
        '16615164',
        '16690745',
        '16833591',
        '16920391',
        '16935990',
        '17406400',
        '17580179',
    }
    with BSPlayerProvider(search_url=SEARCH_URL) as provider:
        subtitles = provider.query(languages, file_hash=video.hashes['bsplayer'], size=video.size)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_hash(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    languages = {Language('deu'), Language('fra')}
    expected_subtitles = {'21230278', '16456646', '16448284', '16456702'}

    with BSPlayerProvider(search_url=SEARCH_URL) as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    languages = {Language('eng'), Language('spa')}
    with BSPlayerProvider(search_url=SEARCH_URL) as provider:
        subtitles = provider.list_subtitles(video, languages)
        assert len(subtitles) >= 1
        subtitle = subtitles[0]
    provider.download_subtitle(subtitle)
    assert subtitle.content is not None
    assert subtitle.is_valid() is True
