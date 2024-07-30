import os
import sys

import pytest
from babelfish import Language
from subliminal.providers.bsplayer import BSPlayerProvider, BSPlayerSubtitle
from vcr import VCR

vcr = VCR(
    path_transformer=lambda path: path + '.yaml',
    record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
    match_on=['method', 'scheme', 'host', 'port', 'path', 'query', 'body'],
    cassette_library_dir=os.path.realpath(
        os.path.join('tests', 'cassettes', 'bsplayer' if sys.version_info >= (3, 10) else 'bsplayer.py3.9')
    ),
)


def test_get_matches_movie_hash(episodes):
    subtitle = BSPlayerSubtitle(
        subtitle_id='16442520',
        size=12185,
        page_link=None,
        language=Language('spa'),
        filename='The.Big.Bang.Theory.S07E05.720p.HDTV.X264-DIMENSION.srt',
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
        movie_fps=0,
    )

    matches = subtitle.get_matches(episodes['bbt_s07e05'])
    assert matches == {'hash'}


@pytest.mark.integration()
@vcr.use_cassette
def test_login():
    provider = BSPlayerProvider(search_url='http://s1.api.bsplayer-subtitles.com/v1.php')
    assert provider.token is None
    provider.initialize()
    assert provider.token is not None


@pytest.mark.integration()
@vcr.use_cassette
def test_logout():
    provider = BSPlayerProvider(search_url='http://s1.api.bsplayer-subtitles.com/v1.php')
    provider.initialize()
    provider.terminate()
    assert provider.token is None


@pytest.mark.integration()
@vcr.use_cassette
def test_query_hash_size(movies):
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
    with BSPlayerProvider(search_url='http://s1.api.bsplayer-subtitles.com/v1.php') as provider:
        subtitles = provider.query(languages, file_hash=video.hashes['bsplayer'], size=video.size)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration()
@vcr.use_cassette
def test_list_subtitles_hash(movies):
    video = movies['man_of_steel']
    languages = {Language('deu'), Language('fra')}
    expected_subtitles = {'21230278', '16456646', '16448284', '16456702'}

    with BSPlayerProvider(search_url='http://s2.api.bsplayer-subtitles.com/v1.php') as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration()
@vcr.use_cassette
def test_download_subtitle(episodes):
    video = episodes['bbt_s07e05']
    languages = {Language('eng'), Language('spa')}
    with BSPlayerProvider(search_url='http://s3.api.bsplayer-subtitles.com/v1.php') as provider:
        subtitles = provider.list_subtitles(video, languages)
        provider.download_subtitle(subtitles[0])
    assert subtitles[0].content is not None
    assert subtitles[0].is_valid() is True
