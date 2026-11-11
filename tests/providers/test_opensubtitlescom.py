from __future__ import annotations

import asyncio
import contextlib
import os
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import aiohttp
import pytest
from babelfish import Language  # type: ignore[import-untyped]
from vcr import VCR  # type: ignore[import-untyped]

from subliminal.exceptions import ConfigurationError, DiscardingError
from subliminal.providers.opensubtitlescom import (
    OpenSubtitlesComError,
    OpenSubtitlesComProvider,
    OpenSubtitlesComSubtitle,
    Unauthorized,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from vcr.request import Request

    from subliminal.video import Episode, Movie


USERNAME = 'python-subliminal-test'
PASSWORD = 'subliminal'


# Bug with vcrpy and aiohttp, POST body is not recorded as a str but as a dict
def before_record_cb(request: Request) -> Request:
    body = request.body
    if body:
        if isinstance(body, bytes):
            # Decode bytes to str
            body = body.decode('utf-8')
        request.body = str(body).replace("'", '"').encode('utf-8')
    return request


vcr = VCR(
    path_transformer=lambda path: path + '.yaml',
    before_record_request=before_record_cb,
    record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
    decode_compressed_response=True,
    match_on=['method', 'scheme', 'host', 'port', 'path', 'query', 'body'],
    cassette_library_dir=os.path.realpath(os.path.join('tests', 'cassettes', 'opensubtitlescom')),
)


def test_get_matches_movie_hash(movies: dict[str, Movie]) -> None:
    subtitle = OpenSubtitlesComSubtitle(
        language=Language('deu'),
        subtitle_id='1953771409',
        hearing_impaired=False,
        movie_kind='movie',
        movie_title='Man of Steel',
        release='Man.of.Steel.German.720p.BluRay.x264-EXQUiSiTE',
        movie_year=2013,
        movie_imdb_id='tt0770828',
        series_season=0,
        series_episode=0,
        moviehash_match=True,
        file_name='Man.of.Steel.German.720p.BluRay.x264-EXQUiSiTE.srt',
    )
    matches = subtitle.get_matches(movies['man_of_steel'])
    assert matches == {
        'title',
        'year',
        'country',
        'video_codec',
        'resolution',
        'source',
        'hash',
    }


def test_get_matches_episode(episodes: dict[str, Episode]) -> None:
    subtitle = OpenSubtitlesComSubtitle(
        language=Language('ell'),
        subtitle_id='1953579014',
        hearing_impaired=False,
        movie_kind='episode',
        movie_title='Mhysa',
        release=' Game.of.Thrones.S03E10.HDTV.XviD-AFG',
        movie_year=2013,
        movie_imdb_id='tt2178796',
        series_title='Game of Thrones',
        series_season=3,
        series_episode=10,
        file_name='Game.of.Thrones.S03E10.HDTV.XviD-AFG.srt',
    )
    matches = subtitle.get_matches(episodes['got_s03e10'])
    assert matches == {
        'series',
        'year',
        'country',
        'episode',
        'season',
        'title',
    }


def test_get_matches_episode_year(episodes: dict[str, Episode]) -> None:
    subtitle = OpenSubtitlesComSubtitle(
        language=Language('spa'),
        subtitle_id='1953369959',
        hearing_impaired=False,
        movie_kind='episode',
        movie_title='The Price You Pay',
        release=' Dallas.2012.S01E03.HDTV.x264-LOL',
        movie_year=2012,
        movie_imdb_id='tt2205526',
        series_title='Dallas',
        series_season=1,
        series_episode=3,
        file_name='Dallas.2012.S01E03.HDTV.x264-LOL.srt',
    )
    matches = subtitle.get_matches(episodes['dallas_2012_s01e03'])
    assert matches == {'series', 'year', 'episode', 'season', 'title'}


def test_get_matches_episode_filename(episodes: dict[str, Episode]) -> None:
    subtitle = OpenSubtitlesComSubtitle(
        language=Language('por', country='BR'),
        subtitle_id='1954453973',
        hearing_impaired=False,
        movie_kind='episode',
        movie_title='A Fractured House',
        release='HDTV.x264-KILLERS-mSD-AFG-EVO-KILLERS',
        movie_year=2014,
        movie_imdb_id='tt4078580',
        series_title='Agents of S.H.I.E.L.D.',
        series_season=2,
        series_episode=6,
        file_name='Marvels.Agents.of.S.H.I.E.L.D.S02E06.720p.HDTV.x264-KILLERS.srt',
    )
    matches = subtitle.get_matches(episodes['marvels_agents_of_shield_s02e06'])
    assert matches == {
        'series',
        'year',
        'country',
        'season',
        'episode',
        'release_group',
        'source',
        'resolution',
        'video_codec',
    }


def test_get_matches_episode_tag(episodes: dict[str, Episode]) -> None:
    subtitle = OpenSubtitlesComSubtitle(
        language=Language('por', country='BR'),
        subtitle_id='1954453973',
        hearing_impaired=False,
        movie_kind='episode',
        movie_title='A Fractured House',
        release='HDTV.x264-KILLERS-mSD-AFG-EVO-KILLERS',
        movie_year=2014,
        movie_imdb_id='tt4078580',
        series_title='Agents of S.H.I.E.L.D.',
        series_season=2,
        series_episode=6,
        file_name='',
    )
    matches = subtitle.get_matches(episodes['marvels_agents_of_shield_s02e06'])
    assert matches == {
        'year',
        'country',
        'season',
        'episode',
        'source',
        'video_codec',
    }


def test_get_matches_imdb_id(movies: dict[str, Movie]) -> None:
    subtitle = OpenSubtitlesComSubtitle(
        language=Language('fra'),
        subtitle_id='1953767650',
        hearing_impaired=True,
        movie_kind='movie',
        movie_title='Man of Steel',
        release='man.of.steel.2013.720p.bluray.x264-felony',
        movie_year=2013,
        movie_imdb_id='tt0770828',
        imdb_match=True,
        series_season=0,
        series_episode=0,
        file_name='man.of.steel.2013.720p.bluray.x264-felony.srt',
    )
    matches = subtitle.get_matches(movies['man_of_steel'])
    assert matches == {
        'title',
        'year',
        'country',
        'video_codec',
        'imdb_id',
        'resolution',
        'source',
        'release_group',
    }


def test_get_matches_no_match(episodes: dict[str, Episode]) -> None:
    subtitle = OpenSubtitlesComSubtitle(
        language=Language('fra'),
        subtitle_id='1953767650',
        hearing_impaired=False,
        movie_kind='movie',
        movie_title='Man of Steel',
        release='man.of.steel.2013.720p.bluray.x264-felony',
        movie_year=2013,
        movie_imdb_id='770828',
        series_season=0,
        series_episode=0,
        file_name='man.of.steel.2013.720p.bluray.x264-felony.srt',
    )
    matches = subtitle.get_matches(episodes['got_s03e10'])
    assert matches == set()


def test_make_criteria_show_imdb_id() -> None:
    provider = OpenSubtitlesComProvider(USERNAME, PASSWORD)
    criteria = provider._make_criteria(query='The Big Bang Theory', season=7, episode=5, show_imdb_id='tt0898266')
    assert criteria[0] == {
        'type': 'episode',
        'parent_imdb_id': 898266,
        'query': 'The Big Bang Theory',
        'season_number': 7,
        'episode_number': 5,
    }
    assert {'type': 'episode', 'parent_imdb_id': 898266, 'season_number': 7, 'episode_number': 5} in criteria


def test_make_criteria_show_tmdb_id() -> None:
    provider = OpenSubtitlesComProvider(USERNAME, PASSWORD)
    criteria = provider._make_criteria(query='The Big Bang Theory', season=7, episode=5, show_tmdb_id='1418')
    assert criteria[0] == {
        'type': 'episode',
        'parent_tmdb_id': 1418,
        'query': 'The Big Bang Theory',
        'season_number': 7,
        'episode_number': 5,
    }
    assert {'type': 'episode', 'parent_tmdb_id': 1418, 'season_number': 7, 'episode_number': 5} in criteria


def test_configuration_error_no_username() -> None:
    with pytest.raises(ConfigurationError):
        OpenSubtitlesComProvider(password=PASSWORD)


def test_configuration_error_no_password() -> None:
    with pytest.raises(ConfigurationError):
        OpenSubtitlesComProvider(username=USERNAME)


@pytest.mark.integration
@pytest.mark.asyncio
@vcr.use_cassette
async def test_login() -> None:
    provider = OpenSubtitlesComProvider(USERNAME, PASSWORD)
    try:
        assert provider.token is None
        await provider.initialize()
        await asyncio.sleep(1)
        await provider.login()
        assert provider.token is not None
    finally:
        await provider.terminate()


@pytest.mark.integration
@pytest.mark.asyncio
@vcr.use_cassette
async def test_login_bad_password() -> None:
    provider = OpenSubtitlesComProvider(USERNAME, 'lanimilbus')
    try:
        with pytest.raises(Unauthorized):  # noqa: PT012
            await provider.initialize()
            await asyncio.sleep(1)
            await provider.login()
    finally:
        await provider.terminate()


@pytest.mark.integration
@pytest.mark.asyncio
@vcr.use_cassette
async def test_logout() -> None:
    provider = OpenSubtitlesComProvider(USERNAME, PASSWORD)
    await provider.initialize()
    await asyncio.sleep(1)
    await provider.login()
    await provider.terminate()
    assert provider.token is None


@pytest.mark.integration
@pytest.mark.asyncio
@vcr.use_cassette
async def test_query_not_enough_information() -> None:
    languages = {Language('eng')}
    async with OpenSubtitlesComProvider(USERNAME, PASSWORD) as provider:
        with pytest.raises(ValueError) as excinfo:  # noqa: PT011
            await provider.query(languages)
    assert str(excinfo.value) == 'Not enough information'


@pytest.mark.integration
@pytest.mark.asyncio
@vcr.use_cassette
async def test_query_query_movie(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    languages = {Language('fra')}
    expected_subtitles = {
        '870964',
        '877697',
        '879122',
        '880511',
    }
    async with OpenSubtitlesComProvider(USERNAME, PASSWORD) as provider:
        subtitles = await provider.query(languages, query=video.title)
    assert expected_subtitles <= {subtitle.id for subtitle in subtitles}
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@pytest.mark.asyncio
@vcr.use_cassette
async def test_query_query_episode(episodes: dict[str, Episode]) -> None:
    video = episodes['dallas_2012_s01e03']
    languages = {Language('fra')}
    expected_subtitles = {'3829531'}
    async with OpenSubtitlesComProvider(USERNAME, PASSWORD) as provider:
        subtitles = await provider.query(languages, query=video.series, season=video.season, episode=video.episode)
    assert expected_subtitles <= {subtitle.id for subtitle in subtitles}
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@pytest.mark.asyncio
@vcr.use_cassette
async def test_query_tag_movie(movies: dict[str, Movie]) -> None:
    video = movies['enders_game']
    languages = {Language('fra')}
    expected_subtitles = {'938965', '940630'}
    async with OpenSubtitlesComProvider(USERNAME, PASSWORD) as provider:
        subtitles = await provider.query(languages, query=video.name)
    assert expected_subtitles <= {subtitle.id for subtitle in subtitles}
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@pytest.mark.asyncio
@vcr.use_cassette
async def test_query_imdb_id(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    languages = {Language('deu')}
    expected_subtitles = {
        '880332',
        '880717',
        '883552',
        '883560',
        '883668',
        '5166256',
        '6632511',
    }
    async with OpenSubtitlesComProvider(USERNAME, PASSWORD) as provider:
        subtitles = await provider.query(languages, imdb_id=video.external_ids.get('imdb_id'))
    assert expected_subtitles <= {subtitle.id for subtitle in subtitles}
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@pytest.mark.asyncio
@vcr.use_cassette
async def test_query_hash_size(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    languages = {Language('eng')}
    expected_subtitles = {
        '869742',
        '871951',
        '872093',
        '873226',
        '874537',
        '876180',
        '876365',
        '877376',
        '877471',
        '879204',
        '882182',
    }
    async with OpenSubtitlesComProvider(USERNAME, PASSWORD) as provider:
        subtitles = await provider.query(languages, moviehash=video.hashes['opensubtitlescom'])
    assert expected_subtitles <= {subtitle.id for subtitle in subtitles}
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@pytest.mark.asyncio
@vcr.use_cassette
async def test_query_wrong_hash_wrong_size() -> None:
    languages = {Language('eng')}
    async with OpenSubtitlesComProvider(USERNAME, PASSWORD) as provider:
        with pytest.raises(OpenSubtitlesComError):
            await provider.query(languages, moviehash='123456787654321')


@pytest.mark.integration
@pytest.mark.asyncio
@vcr.use_cassette
async def test_query_query_season_episode(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    languages = {Language('deu')}
    expected_subtitles = {'2748964', '4662161'}
    async with OpenSubtitlesComProvider(USERNAME, PASSWORD) as provider:
        subtitles = await provider.query(languages, query=video.series, season=video.season, episode=video.episode)
    assert expected_subtitles <= {subtitle.id for subtitle in subtitles}
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@pytest.mark.asyncio
@vcr.use_cassette
async def test_list_subtitles_movie(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    languages = {Language('deu'), Language('fra')}
    expected_subtitles = {
        '823209',
        '870964',
        '877697',
        '879122',
        '880332',
        '880511',
        '880717',
        '883552',
        '883560',
        '5166256',
        '6632511',
    }
    async with OpenSubtitlesComProvider(USERNAME, PASSWORD) as provider:
        subtitles = await provider.list_subtitles(video, languages)
    assert expected_subtitles <= {subtitle.id for subtitle in subtitles}
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@pytest.mark.asyncio
@vcr.use_cassette
async def test_list_subtitles_movie_no_hash(movies: dict[str, Movie]) -> None:
    video = movies['enders_game']
    languages = {Language('deu')}
    expected_subtitles = {'939532', '939553', '940426'}
    async with OpenSubtitlesComProvider(USERNAME, PASSWORD) as provider:
        subtitles = await provider.list_subtitles(video, languages)
    assert expected_subtitles <= {subtitle.id for subtitle in subtitles}
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@pytest.mark.asyncio
@vcr.use_cassette
async def test_list_subtitles_episode(episodes: dict[str, Episode]) -> None:
    video = episodes['marvels_agents_of_shield_s02e06']
    languages = {Language('hun')}
    expected_subtitles = {'2491535', '2492310', '2493688'}
    async with OpenSubtitlesComProvider(USERNAME, PASSWORD) as provider:
        subtitles = await provider.list_subtitles(video, languages)
    assert expected_subtitles <= {subtitle.id for subtitle in subtitles}
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@pytest.mark.asyncio
@vcr.use_cassette
async def test_download_subtitle(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    languages = {Language('deu'), Language('fra')}
    async with OpenSubtitlesComProvider(USERNAME, PASSWORD) as provider:
        subtitles = await provider.list_subtitles(video, languages)
        await provider.download_subtitle(subtitles[0])
    assert subtitles[0].content is not None
    assert subtitles[0].is_valid() is True
    assert subtitles[0].encoding == 'utf-8'


@pytest.mark.parametrize('clear', [False, pytest.param(True, marks=[pytest.mark.skip])])
@pytest.mark.integration
@pytest.mark.asyncio
@vcr.use_cassette
async def test_list_subtitles_episode_series_imdb_id(episodes: dict[str, Episode], clear: bool) -> None:
    # folder named after a localized title: the show's IMDb id finds the episode, the title alone does not
    video = episodes['die_sopranos_s01e01']
    languages = {Language('eng')}

    # Clear external ids beforehand, to make the search harder
    if clear:
        video.external_ids.clear()  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]

    async with OpenSubtitlesComProvider(USERNAME, PASSWORD) as provider:
        subtitles = await provider.list_subtitles(video, languages)

    if clear:
        assert len(subtitles) == 0
    else:
        assert len(subtitles) > 0
        assert {subtitle.series_title for subtitle in subtitles if subtitle.movie_kind == 'episode'} == {'The Sopranos'}
        assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@pytest.mark.asyncio
@vcr.use_cassette
async def test_query_max_result_pages(movies: dict[str, Movie]) -> None:
    # choose a movie with a lot of results
    query = 'James Bond'
    languages = {Language('eng')}

    async with OpenSubtitlesComProvider(USERNAME, PASSWORD, max_result_pages=0) as provider:
        all_subtitles = await provider.query(languages, query=query)

    await asyncio.sleep(1)

    async with OpenSubtitlesComProvider(USERNAME, PASSWORD, max_result_pages=1) as provider:
        subtitles = await provider.query(languages, query=query)
    assert len(subtitles) < len(all_subtitles)


@pytest.mark.asyncio
async def test_search_keeps_results_when_a_page_fails() -> None:
    """Pagination stops at the failing page and keeps the results already found."""

    @contextlib.asynccontextmanager
    async def _request(method: str, path: str, params: dict[str, Any], **kwargs: Any) -> AsyncGenerator[MagicMock]:
        page = int(params['page'])
        kwargs = {'status': 200, 'reason': None}
        if page >= 3:
            kwargs = {'status': 600, 'reason': 'Connection dropped'}
        response = MagicMock(spec=aiohttp.ClientResponse, **kwargs)
        response.json.return_value = {'data': [{'id': page}], 'total_pages': 100}
        yield response

    async with OpenSubtitlesComProvider(USERNAME, PASSWORD) as provider:
        with patch.object(provider._session, 'request', side_effect=_request):
            results = list(await provider._search(query='Man of Steel'))

    assert [result['id'] for result in results] == [1, 2]


@pytest.mark.asyncio
async def test_search_cancelling_error() -> None:

    @contextlib.asynccontextmanager
    async def _request(method: str, path: str, params: dict[str, Any], **kwargs: Any) -> AsyncGenerator[MagicMock]:
        page = int(params['page'])
        kwargs = {'status': 200, 'reason': None}
        if page == 3:
            raise asyncio.CancelledError
        response = MagicMock(spec=aiohttp.ClientResponse, **kwargs)
        response.json.return_value = {'data': [{'id': page}], 'total_pages': 100}
        yield response

    async with OpenSubtitlesComProvider(USERNAME, PASSWORD) as provider:
        with patch.object(provider._session, 'request', side_effect=_request), pytest.raises(asyncio.CancelledError):
            list(await provider._search(query='Man of Steel'))


@pytest.mark.asyncio
async def test_search_discarding_error() -> None:
    """An error that discards the provider is raised, even in the middle of the pagination."""

    @contextlib.asynccontextmanager
    async def _request(method: str, path: str, params: dict[str, Any], **kwargs: Any) -> AsyncGenerator[MagicMock]:
        page = int(params['page'])
        kwargs = {'status': 200, 'reason': None}
        if page >= 3:
            kwargs = {'status': 503, 'reason': 'Bad request'}
        response = MagicMock(spec=aiohttp.ClientResponse, **kwargs)
        response.json.return_value = {'data': [{'id': page}], 'total_pages': 100}
        yield response

    async with OpenSubtitlesComProvider(USERNAME, PASSWORD) as provider:
        with patch.object(provider._session, 'request', side_effect=_request), pytest.raises(DiscardingError):
            list(await provider._search(query='Man of Steel'))
