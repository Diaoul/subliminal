from __future__ import annotations

import asyncio
import contextlib
import os
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from babelfish import Language  # type: ignore[import-untyped]
from vcr import VCR  # type: ignore[import-untyped]

from subliminal.cache import region
from subliminal.exceptions import (
    AuthenticationError,
    ConfigurationError,
    DiscardingError,
    NotInitializedProviderError,
    ServiceUnavailable,
)
from subliminal.providers.opensubtitlescom import (
    TOKEN_CACHE_KEY,
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


def test_make_criteria_year() -> None:
    provider = OpenSubtitlesComProvider(USERNAME, PASSWORD)
    criteria = provider._make_criteria(query='Man of Steel', year=2013)
    assert criteria[0] == {'type': 'movie', 'query': 'Man of Steel', 'year': 2013}


def test_configuration_error_no_username() -> None:
    with pytest.raises(ConfigurationError):
        OpenSubtitlesComProvider(password=PASSWORD)


def test_configuration_error_no_password() -> None:
    with pytest.raises(ConfigurationError):
        OpenSubtitlesComProvider(username=USERNAME)


def test_session_not_initialized() -> None:
    provider = OpenSubtitlesComProvider(USERNAME, PASSWORD)
    with pytest.raises(NotInitializedProviderError):
        provider.session  # noqa: B018


@pytest.mark.asyncio
async def test_given_session_is_not_closed_by_the_provider() -> None:
    async with aiohttp.ClientSession() as session:
        async with OpenSubtitlesComProvider(USERNAME, PASSWORD, session=session) as provider:
            assert provider.session is session
        assert not session.closed


@pytest.mark.asyncio
async def test_check_token_expired() -> None:
    provider = OpenSubtitlesComProvider(USERNAME, PASSWORD)
    provider.token = 'expired-token'
    provider.token_expires_at = datetime.now(UTC) - timedelta(seconds=1)

    # the cache is empty in the tests
    assert not await provider.check_token()
    assert provider.token is None
    assert provider.token_expires_at is None


@pytest.mark.asyncio
async def test_check_token_from_cache() -> None:
    provider = OpenSubtitlesComProvider(USERNAME, PASSWORD)

    with patch.object(region, 'get', return_value='cached-token') as get:
        assert await provider.check_token()
    get.assert_called_once()
    assert provider.token == 'cached-token'
    assert provider.token_expires_at is not None
    assert provider.token_expires_at > datetime.now(UTC)

    # the token is now valid, the cache is not needed anymore
    with patch.object(region, 'get') as get:
        assert await provider.check_token()
    get.assert_not_called()


@pytest.mark.asyncio
async def test_reset_token() -> None:
    provider = OpenSubtitlesComProvider(USERNAME, PASSWORD)
    provider.token = 'stale-token'
    provider.token_expires_at = datetime.now(UTC) + timedelta(hours=1)

    with patch.object(region, 'delete') as delete:
        await provider.reset_token()

    delete.assert_called_once_with(TOKEN_CACHE_KEY)
    assert provider.token is None
    assert provider.token_expires_at is None


@pytest.mark.asyncio
async def test_ensure_authenticated_valid_token_skips_login() -> None:
    async with OpenSubtitlesComProvider(USERNAME, PASSWORD) as provider:
        provider.token = 'valid-token'
        provider.token_expires_at = datetime.now(UTC) + timedelta(hours=1)

        with patch.object(provider, 'login', new_callable=AsyncMock) as login:
            await provider.ensure_authenticated()

    login.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_authenticated_logs_in() -> None:
    async with OpenSubtitlesComProvider(USERNAME, PASSWORD) as provider:

        async def login() -> None:
            provider.token = 'new-token'
            provider.token_expires_at = datetime.now(UTC) + timedelta(hours=1)

        with patch.object(provider, 'login', side_effect=login) as mock_login:
            await provider.ensure_authenticated()

        mock_login.assert_awaited_once()
        assert provider.token == 'new-token'


@pytest.mark.asyncio
async def test_ensure_authenticated_login_without_token() -> None:
    """A login that does not give a token is an authentication error."""
    async with OpenSubtitlesComProvider(USERNAME, PASSWORD) as provider:
        with (
            patch.object(provider, 'login', new_callable=AsyncMock) as login,
            pytest.raises(AuthenticationError),
        ):
            await provider.ensure_authenticated()

    login.assert_awaited_once()


@pytest.mark.asyncio
async def test_request_unauthorized_logs_in_again_and_retries() -> None:
    """A stale token gives a '401 Unauthorized': the token is dropped and the request is sent again."""
    urls: list[str] = []

    @contextlib.asynccontextmanager
    async def _request(method: str, url: str, **kwargs: Any) -> AsyncGenerator[MagicMock]:
        urls.append(url)
        attrs: dict[str, Any] = {'status': 200, 'reason': None}
        if len(urls) == 1:
            attrs = {'status': 401, 'reason': 'Unauthorized'}
        response = MagicMock(spec=aiohttp.ClientResponse, **attrs)
        response.json.return_value = {'data': 'ok'}
        yield response

    async with OpenSubtitlesComProvider(USERNAME, PASSWORD) as provider:
        with (
            patch.object(provider._session, 'request', side_effect=_request),
            patch.object(provider, 'ensure_authenticated', new_callable=AsyncMock) as ensure_authenticated,
            patch.object(provider, 'reset_token', new_callable=AsyncMock) as reset_token,
        ):
            result = await provider._request('GET', 'subtitles', authenticated=True)

    assert result == {'data': 'ok'}
    assert len(urls) == 2
    assert ensure_authenticated.await_count == 2
    reset_token.assert_awaited_once()


@pytest.mark.asyncio
async def test_request_too_many_retries() -> None:
    """The requests are rate limited at each attempt, until the retries are exhausted."""
    urls: list[str] = []

    @contextlib.asynccontextmanager
    async def _request(method: str, url: str, **kwargs: Any) -> AsyncGenerator[MagicMock]:
        urls.append(url)
        yield MagicMock(
            spec=aiohttp.ClientResponse,
            status=429,
            reason='Too Many Requests',
            headers={'Retry-After': '0'},
        )

    async with OpenSubtitlesComProvider(USERNAME, PASSWORD, max_retries=2) as provider:
        with (
            patch.object(provider._session, 'request', side_effect=_request),
            pytest.raises(ServiceUnavailable),
        ):
            await provider._request('GET', 'subtitles')

    assert len(urls) == 2


@pytest.mark.asyncio
async def test_search_failing_page_with_requests_in_flight() -> None:
    """Pages in flight are kept and the pages still waiting are not requested after a failure."""
    requested: list[int] = []

    @contextlib.asynccontextmanager
    async def _request(method: str, path: str, params: dict[str, Any], **kwargs: Any) -> AsyncGenerator[MagicMock]:
        page = int(params['page'])
        requested.append(page)
        kwargs = {'status': 200, 'reason': None}
        if page == 3:
            kwargs = {'status': 600, 'reason': 'Connection dropped'}
        # page 3 fails while the other pages are still in flight
        await asyncio.sleep(0.01 if page == 3 else 0.05)
        response = MagicMock(spec=aiohttp.ClientResponse, **kwargs)
        response.json.return_value = {'data': [{'id': page}], 'total_pages': 100}
        yield response

    async with OpenSubtitlesComProvider(USERNAME, PASSWORD, max_concurrent_requests=5) as provider:
        with patch.object(provider._session, 'request', side_effect=_request):
            results = list(await provider._search(query='Man of Steel'))

    # the pages in flight when page 3 failed are not cancelled, the following ones are not requested
    assert sorted(requested) == [1, 2, 3, 4, 5, 6]
    assert sorted(result['id'] for result in results) == [1, 2, 4, 5, 6]


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
@vcr.use_cassette(allow_playback_repeats=True)  # the same query is sent twice, for page=1
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
