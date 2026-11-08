"""Provider for Opensubtitles.com."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import sys
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, ClassVar

if sys.version_info >= (3, 12):
    from typing import override
else:  # pragma: no cover
    from typing_extensions import override

import aiohttp
from babelfish import Language, language_converters  # type: ignore[import-untyped]
from dogpile.cache.api import NO_VALUE

from subliminal import __short_version__
from subliminal.cache import region
from subliminal.exceptions import (
    AuthenticationError,
    ConfigurationError,
    DiscardingError,
    DownloadLimitExceeded,
    NotInitializedProviderError,
    ProviderError,
    ServiceUnavailable,
)
from subliminal.matches import guess_matches
from subliminal.subtitle import Subtitle
from subliminal.utils import safely_guessit
from subliminal.video import Episode, Movie, Video

from . import AsyncProvider

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Set
    from typing import TypeVar

    C = TypeVar('C', bound=Callable)


logger = logging.getLogger(__name__)

with contextlib.suppress(ValueError):
    language_converters.register('opensubtitlescom = subliminal.converters.opensubtitlescom:OpenSubtitlesComConverter')

#: Opensubtitles.com API key for subliminal
OPENSUBTITLESCOM_API_KEY = 'mij33pjc3kOlup1qOKxnWWxvle2kFbMH'

#: Expiration time for token
DEFAULT_EXPIRATION_TIME = timedelta(days=1).total_seconds()

#: Expiration time for token
TOKEN_EXPIRATION_TIME = timedelta(hours=24).total_seconds()

#: Expiration time for download link
DOWNLOAD_EXPIRATION_TIME = timedelta(hours=3).total_seconds()

#: Cache key for the authentication token
TOKEN_CACHE_KEY = 'oscom_token'  # noqa: S105


# fmt: off
opensubtitlescom_languages = {
    Language('por', 'BR'),
    Language('srp', 'ME'),
    Language('zho', 'TW'),
    Language('zho', 'US'),
} | {
    Language(lang) for lang in [
        'afr', 'ara', 'arg', 'ast', 'bel', 'ben', 'bos', 'bre', 'bul', 'cat', 'ces', 'dan', 'deu', 'ell', 'eng', 'epo',
        'est', 'eus', 'fas', 'fin', 'fra', 'glg', 'heb', 'hin', 'hrv', 'hun', 'hye', 'ind', 'isl', 'ita', 'jpn', 'kat',
        'kaz', 'khm', 'kor', 'lav', 'lit', 'ltz', 'mal', 'mkd', 'mni', 'mon', 'msa', 'mya', 'nld', 'nor', 'oci', 'pol',
        'ron', 'rus', 'sin', 'slk', 'slv', 'spa', 'sqi', 'srp', 'swa', 'swe', 'syr', 'tam', 'tel', 'tgl', 'tha', 'tur',
        'ukr', 'urd', 'uzb', 'vie'
    ]
}
# fmt: on


def sanitize_id(id_: int | str | None) -> int | None:
    """Sanitize the IMDB (or other) id and transform it to a string (without leading 'tt' or zeroes)."""
    if id_ is None:  # pragma: no cover
        return None
    id_ = str(id_).lower().lstrip('t')
    return int(id_)


def decorate_imdb_id(imdb_id: int | str | None, *, ndigits: int = 7) -> str | None:
    """Convert the IMDB id to string and add the leading zeroes and 'tt'."""
    if imdb_id is None:
        return None
    return 'tt' + str(int(imdb_id)).rjust(ndigits, '0')


class OpenSubtitlesComSubtitle(Subtitle):
    """OpenSubtitles.com Subtitle."""

    provider_name: ClassVar[str] = 'opensubtitlescom'

    movie_kind: str | None
    release: str | None
    movie_title: str | None
    movie_full_name: str | None
    movie_year: int | None
    movie_imdb_id: str | None
    movie_tmdb_id: str | None
    series_title: str | None
    series_season: int | None
    series_episode: int | None
    series_imdb_id: str | None
    series_tmdb_id: str | None
    download_count: int | None
    machine_translated: bool | None
    imdb_match: bool
    tmdb_match: bool
    moviehash_match: bool
    file_id: int
    file_name: str
    fps: float | None

    def __init__(
        self,
        language: Language,
        subtitle_id: str,
        *,
        hearing_impaired: bool = False,
        foreign_only: bool = False,
        movie_kind: str | None = None,
        release: str | None = None,
        movie_title: str | None = None,
        movie_full_name: str | None = None,
        movie_year: int | None = None,
        movie_imdb_id: str | None = None,
        movie_tmdb_id: str | None = None,
        series_title: str | None = None,
        series_season: int | None = None,
        series_episode: int | None = None,
        series_imdb_id: str | None = None,
        series_tmdb_id: str | None = None,
        download_count: int | None = None,
        machine_translated: bool | None = None,
        fps: float | None = None,
        imdb_match: bool = False,
        tmdb_match: bool = False,
        moviehash_match: bool = False,
        file_id: int = 0,
        file_name: str = '',
    ) -> None:
        super().__init__(
            language,
            subtitle_id,
            hearing_impaired=hearing_impaired,
            foreign_only=foreign_only,
            fps=fps,
            page_link=None,
            encoding='utf-8',
        )
        self.movie_kind = movie_kind
        self.release = release
        self.movie_title = movie_title
        self.movie_full_name = movie_full_name
        self.movie_year = movie_year
        self.movie_imdb_id = movie_imdb_id
        self.movie_tmdb_id = movie_tmdb_id
        self.series_title = series_title
        self.series_season = series_season
        self.series_episode = series_episode
        self.series_imdb_id = series_imdb_id
        self.series_tmdb_id = series_tmdb_id
        self.download_count = download_count
        self.machine_translated = machine_translated
        self.imdb_match = imdb_match
        self.tmdb_match = tmdb_match
        self.moviehash_match = moviehash_match
        self.file_id = file_id
        self.file_name = file_name

    @classmethod
    def from_response(
        cls,
        response: dict[str, Any],
        *,
        imdb_match: bool = False,
        tmdb_match: bool = False,
    ) -> OpenSubtitlesComSubtitle:
        """Parse a single subtitle query response to a :class:`OpenSubtitlesComSubtitle`."""
        # read the response
        subtitle_id = str(int(response.get('id')))  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]

        attributes = response.get('attributes', {})
        language = Language.fromopensubtitlescom(str(attributes.get('language')))
        hearing_impaired = bool(int(attributes.get('hearing_impaired')))
        foreign_only = bool(int(attributes.get('foreign_parts_only')))
        release = str(attributes.get('release'))
        moviehash_match = bool(attributes.get('moviehash_match', False))
        download_count = int(attributes.get('download_count'))
        machine_translated = bool(int(attributes.get('machine_translated')))
        fps: float | None = float(attributes.get('fps')) or None
        # from_trusted = bool(int(attributes.get('from_trusted')))
        # uploader_rank = str(attributes.get('uploader', {}).get("rank"))
        # foreign_parts_only = bool(int(attributes.get('foreign_parts_only')))

        feature_details = attributes.get('feature_details', {})
        movie_year = int(feature_details.get('year')) if feature_details.get('year') else None
        movie_title = str(feature_details.get('title'))
        movie_full_name = str(feature_details.get('movie_name'))
        movie_kind = str(feature_details.get('feature_type').lower())
        movie_imdb_id = decorate_imdb_id(feature_details.get('imdb_id'))
        movie_tmdb_id = feature_details.get('tmdb_id')
        series_season = int(feature_details.get('season_number')) if feature_details.get('season_number') else None
        series_episode = int(feature_details.get('episode_number')) if feature_details.get('episode_number') else None
        series_title = str(feature_details.get('parent_title'))
        series_imdb_id = decorate_imdb_id(feature_details.get('parent_imdb_id'))
        series_tmdb_id = feature_details.get('parent_tmdb_id')

        files = attributes.get('files', [])
        srt_file: dict[str, Any] = {'file_id': 0, 'file_name': ''} if len(files) == 0 else files[0]
        file_id = int(srt_file.get('file_id'))  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
        file_name = str(srt_file.get('file_name'))

        return cls(
            language,
            subtitle_id,
            hearing_impaired=hearing_impaired,
            foreign_only=foreign_only,
            movie_kind=movie_kind,
            release=release,
            movie_title=movie_title,
            movie_full_name=movie_full_name,
            movie_year=movie_year,
            movie_imdb_id=movie_imdb_id,
            movie_tmdb_id=movie_tmdb_id,
            series_title=series_title,
            series_season=series_season,
            series_episode=series_episode,
            series_imdb_id=series_imdb_id,
            series_tmdb_id=series_tmdb_id,
            download_count=download_count,
            machine_translated=machine_translated,
            fps=fps,
            imdb_match=imdb_match,
            tmdb_match=tmdb_match,
            moviehash_match=moviehash_match,
            file_id=file_id,
            file_name=file_name,
        )

    @property
    def info(self) -> str:  # pragma: no cover
        """Information about the subtitle."""
        if not self.file_name and not self.release:
            return self.id
        if self.release and len(self.release) > len(self.file_name):
            return self.release
        return self.file_name

    def get_matches(self, video: Video) -> set[str]:
        """Get the matches against the `video`."""
        if (isinstance(video, Episode) and self.movie_kind != 'episode') or (
            isinstance(video, Movie) and self.movie_kind != 'movie'
        ):
            logger.info('%r is not a valid movie_kind', self.movie_kind)
            return set()

        matches = guess_matches(
            video,
            {
                'title': self.series_title if self.movie_kind == 'episode' else self.movie_title,
                'episode_title': self.movie_title if self.movie_kind == 'episode' else None,
                'year': self.movie_year,
                'season': self.series_season,
                'episode': self.series_episode,
                'fps': self.fps,
            },
        )

        # guess
        matches |= guess_matches(video, safely_guessit(self.release, {'type': self.movie_kind}))
        matches |= guess_matches(video, safely_guessit(self.file_name, {'type': self.movie_kind}))

        # imdb_id
        if self.imdb_match:
            matches.add('imdb_id')

        # tmdb_id
        if self.tmdb_match:  # pragma: no cover
            matches.add('tmdb_id')

        # hash match
        if self.moviehash_match:
            matches.add('hash')

        return matches


class OpenSubtitlesComProvider(AsyncProvider):
    """OpenSubtitles.com Provider.

    :param str username: username
    :param str password: password
    :param str apikey: private API key
    :param int max_result_pages: maximum number of result pages to process,
        set to non-zero to search faster, although the correct match can be
        missing. Set to 0 for unlimited result pages. Default to 10.
    :param int timeout: timeout in seconds. Default to 20.
    :param bool allow_machine_generated: if False, skip machine translated subtitles. Default to False.
    :param int max_concurrent_requests: maximum number of requests in flight for this provider.
        Default to 5
    :param int max_retries: maximum number of retries when hitting a 'Too Many Requests' error.
        Default to 3
    :param session: the :class:`aiohttp.ClientSession` to use. The pool injects its own; when
        `None`, the provider creates and closes its own session.

    """

    server_url: ClassVar[str] = 'https://api.opensubtitles.com/api/v1/'
    subtitle_class: ClassVar = OpenSubtitlesComSubtitle
    languages: ClassVar[Set[Language]] = opensubtitlescom_languages

    user_agent: str = f'Subliminal v{__short_version__}'
    subtitle_format: str = 'srt'

    username: str | None
    password: str | None
    apikey: str
    max_result_pages: int
    timeout: int
    allow_machine_generated: bool
    token: str | None
    token_expires_at: datetime | None

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        *,
        apikey: str | None = None,
        max_result_pages: int = 10,
        timeout: int = 20,
        allow_machine_generated: bool = False,
        max_concurrent_requests: int = 5,
        max_retries: int = 3,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        if any((username, password)) and not all((username, password)):
            msg = 'Username and password must be specified'
            raise ConfigurationError(msg)

        self.username = username
        self.password = password
        self.apikey = apikey or OPENSUBTITLESCOM_API_KEY
        self.max_result_pages = max_result_pages
        self.timeout = timeout
        self.allow_machine_generated = allow_machine_generated
        self.max_retries = max_retries
        self.token = None
        self.token_expires_at = None

        self._session = session
        self._owns_session = session is None
        self._max_concurrent_requests = max(1, max_concurrent_requests)
        self._semaphore: asyncio.Semaphore | None = None
        self._login_lock: asyncio.Lock | None = None

    @property
    def session(self) -> aiohttp.ClientSession:
        """The :class:`aiohttp.ClientSession` in use."""
        if self._session is None:
            raise NotInitializedProviderError
        return self._session

    @override
    async def initialize(self) -> None:
        """Initialize the provider.

        No network call is made here: authentication is lazy, so a provider that ends up
        being skipped for a given video never pays for a login.
        """
        self._semaphore = asyncio.Semaphore(self._max_concurrent_requests)
        self._login_lock = asyncio.Lock()

        if self._session is None:
            self._session = aiohttp.ClientSession()
            self._owns_session = True

    @override
    async def terminate(self) -> None:
        """Terminate the provider."""
        # Clear token
        self.token = None
        self.token_expires_at = None

        if self._owns_session and self._session is not None:
            await self._session.close()
            self._session = None

    # ------------------------------------------------------------------
    # authentication
    # ------------------------------------------------------------------

    def _headers(self, *, authenticated: bool = False) -> dict[str, str]:
        """Build the headers of a request.

        The session is shared with other async providers, so headers are never stored on it.
        """
        headers = {
            'User-Agent': self.user_agent,
            'Api-Key': self.apikey,
            'Accept': '*/*',
            'Content-Type': 'application/json',
        }
        if authenticated and self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        return headers

    async def check_token(self) -> bool:
        """Return `True` if a valid token is available, loading it from the cache if needed."""
        if self.token is not None and self.token_expires_at is not None:
            if datetime.now(UTC) < self.token_expires_at:
                return True
            # expired
            self.token = None
            self.token_expires_at = None

        # the dogpile region is backed by a file, do not block the event loop
        token = await asyncio.to_thread(region.get, TOKEN_CACHE_KEY, expiration_time=TOKEN_EXPIRATION_TIME)
        if token is NO_VALUE:
            return False

        self.token = str(token)
        self.token_expires_at = datetime.now(UTC) + timedelta(seconds=TOKEN_EXPIRATION_TIME)
        return True

    async def login(self) -> None:
        """Log in and store the token, in the instance and in the cache."""
        if not self.username or not self.password:  # pragma: no cover
            logger.info('Cannot log in, a username and password must be provided')
            return

        logger.info('Logging in')
        data = {'username': self.username, 'password': self.password}
        response = await self._request('POST', 'login', json=data)

        token = response.get('token')
        if not token:  # pragma: no cover
            logger.debug('Error, the authentication token is empty.')
            return

        self.token = str(token)
        self.token_expires_at = datetime.now(UTC) + timedelta(seconds=TOKEN_EXPIRATION_TIME)
        await asyncio.to_thread(region.set, TOKEN_CACHE_KEY, self.token)

        logger.debug('Logged in')

    async def reset_token(self) -> None:
        """Drop the authentication token, from the instance and from the cache."""
        logger.debug('Authentication failed: clearing cache and attempting to login.')
        self.token = None
        self.token_expires_at = None
        await asyncio.to_thread(region.delete, TOKEN_CACHE_KEY)

    async def ensure_authenticated(self) -> None:
        """Make sure a valid token is available, logging in if needed.

        The lock makes concurrent callers wait for a single login instead of racing.
        """
        if await self.check_token():
            return

        if self._login_lock is None:  # pragma: no cover
            raise NotInitializedProviderError

        async with self._login_lock:
            # another coroutine may have logged in while waiting for the lock
            if await self.check_token():  # pragma: no cover
                return

            await self.login()

            if not await self.check_token():
                msg = 'Cannot authenticate with username and password'
                raise AuthenticationError(msg)

    # ------------------------------------------------------------------
    # HTTP
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Mapping[str, Any] | None = None,
        authenticated: bool = False,
        raises: bool = True,
    ) -> dict[str, Any]:
        """Make a request to the API and return the decoded JSON body.

        Retries on '429 Too Many Requests', honoring the ``Retry-After`` header, and retries
        once on '401 Unauthorized' after a fresh login, as the cached token may be stale.
        """
        if self._semaphore is None:  # pragma: no cover
            raise NotInitializedProviderError

        url = path if path.startswith('http') else self.server_url + path

        if params:
            # sort and lowercase, the API is picky and it keeps the cache keys stable
            params = dict(sorted(params.items()))
            # aiohttp does not accept None or non-string scalars in params
            params = {
                k.lower(): (v.lower() if isinstance(v, str) else str(v)) for k, v in params.items() if v is not None
            }

        retried_auth = False
        for attempt in range(self.max_retries):
            if authenticated:
                await self.ensure_authenticated()

            if attempt > 0:  # pragma: no cover
                msg = f'Attempt #{attempt} to request url: {url}'
                logger.debug(msg)

            try:
                async with (
                    self._semaphore,
                    self.session.request(
                        method,
                        url,
                        params=params,
                        json=dict(json) if json is not None else None,
                        headers=self._headers(authenticated=authenticated),
                        timeout=aiohttp.ClientTimeout(total=self.timeout),
                    ) as response,
                ):
                    if response.status == 429:
                        delay = float(response.headers.get('Retry-After', 1))
                        logger.info('Rate limited, waiting %.1fs before retrying', delay)
                        await asyncio.sleep(delay)
                        continue

                    check_status(response.status, response.reason)
                    # the API is not always honest about its content type
                    return await response.json(content_type=None)  # type: ignore[no-any-return]

            except Unauthorized:
                if retried_auth or not authenticated:
                    if raises:
                        raise
                    # pragma: no cover
                    logger.exception('An error occurred')
                    return {}
                # the cached token is stale, drop it and log in again
                retried_auth = True
                await self.reset_token()
                continue

            except ProviderError:
                if raises:
                    raise
                # pragma: no cover
                logger.exception('An error occurred')
                return {}

        # pragma: no cover
        msg = f'Too many retries for {method} {path}'
        if raises:
            raise ServiceUnavailable(msg)
        return {}

    # ------------------------------------------------------------------
    # search
    # ------------------------------------------------------------------

    def _make_criteria(
        self,
        *,
        moviehash: str | None = None,
        imdb_id: str | None = None,
        tmdb_id: str | None = None,
        query: str | None = None,
        season: int | None = None,
        episode: int | None = None,
        opensubtitles_id: str | None = None,
        show_imdb_id: str | None = None,
        show_tmdb_id: str | None = None,
        year: int | None = None,
    ) -> list[dict[str, Any]]:
        """Build the list of search criteria, from the most specific to the broadest."""
        criterion: dict[str, Any] = {}

        if moviehash:
            criterion['moviehash'] = moviehash

        if imdb_id:
            criterion['imdb_id'] = sanitize_id(imdb_id)
        if show_imdb_id:
            criterion['parent_imdb_id'] = sanitize_id(show_imdb_id)

        if tmdb_id:  # pragma: no cover
            criterion['tmdb_id'] = sanitize_id(tmdb_id)
        if show_tmdb_id:  # pragma: no cover
            criterion['parent_tmdb_id'] = sanitize_id(show_tmdb_id)

        if opensubtitles_id:  # pragma: no cover
            criterion['id'] = opensubtitles_id

        if query:
            criterion['query'] = query.replace("'", '')

        # check for None to allow season=0 and episode=0
        if season is not None and episode is not None:
            criterion['season_number'] = season
            criterion['episode_number'] = episode
        if year:
            criterion['year'] = year

        if not criterion:
            msg = 'Not enough information'
            raise ValueError(msg)

        criteria = [criterion]

        # sometimes, multi-term searches return no result; try minimal searches also
        if len(criterion) > 1:
            # add single-term searches
            for key in ('id', 'imdb_id', 'tmdb_id', 'moviehash'):
                if key in criterion:
                    criteria.append({key: criterion[key]})

            # add single-term searches with season/episode numbers
            if 'season_number' in criterion and 'episode_number' in criterion:
                for key in ('parent_imdb_id', 'parent_tmdb_id', 'query'):
                    if key in criterion:
                        criteria.append(
                            {
                                key: criterion[key],
                                'season_number': criterion['season_number'],
                                'episode_number': criterion['episode_number'],
                            }
                        )
            # add query alone
            if 'query' in criterion:  # pragma: no branch
                criteria.append({'query': criterion['query']})

        # # Make sure the video type is set
        # video_type = 'episode' if season is not None and episode is not None else 'movie'
        # for crit in criteria:
        #     crit['type'] = video_type

        return criteria

    async def _search(self, **params: Any) -> list[dict[str, Any]]:
        """Search subtitles, fetching the result pages concurrently.

        The first page gives the total number of pages, the remaining ones are gathered.
        """
        logger.info('Searching subtitles %r', params)
        first = await self._request('GET', 'subtitles', params={'page': 1, **params}, authenticated=False)

        data: list[dict[str, Any]] = list(first.get('data') or [])
        if not data:
            return []

        total_pages = int(first.get('total_pages', 1) or 1)
        last_page = total_pages
        if self.max_result_pages > 0:
            last_page = min(last_page, self.max_result_pages)

        if last_page <= 1:
            return data

        # Run async tasks
        tasks = []
        try:
            async with asyncio.TaskGroup() as tg:
                for page in range(2, last_page + 1):
                    tasks.append(
                        tg.create_task(self._request('GET', 'subtitles', params={'page': page, **params}, raises=True))
                    )
        except* asyncio.CancelledError:
            # the caller is shutting down, never swallow this
            raise asyncio.CancelledError from None

        except* DiscardingError:
            raise DiscardingError from None

        except* ProviderError as eg:
            # Just log the error, it is not discarding
            logger.warning('Pagination stopped because of errors: %s', {str(e) for e in eg.exceptions})

        # Collect results
        for i, task in enumerate(tasks, start=2):
            try:
                page_result = task.result()
            except ProviderError:
                # ProviderError were not raised when running the task, they can pop up here again
                logger.warning('Error getting page %i', i)
                continue

            data.extend(page_result.get('data') or [])

        return data

    @override
    async def query(
        self,
        languages: Set[Language],
        *,
        sort_by_download_count: bool = True,
        **kwargs: Any,
    ) -> list[OpenSubtitlesComSubtitle]:
        """Query the server and return all the subtitles.

        The different criteria are searched concurrently, then deduplicated.
        """
        criteria = self._make_criteria(**kwargs)
        language_param = ','.join(sorted(lang.opensubtitlescom for lang in languages))

        for criterion in criteria:
            criterion['languages'] = language_param

        # Gather results: no need to handle exceptions, therefore prefer asyncio.gather to asyncio.TaskGroup
        results = await asyncio.gather(*(self._search(**criterion) for criterion in criteria))

        subtitles: list[OpenSubtitlesComSubtitle] = []
        seen: set[str] = set()
        for criterion, responses in zip(criteria, results, strict=True):
            imdb_match = 'imdb_id' in criterion or 'parent_imdb_id' in criterion
            tmdb_match = 'tmdb_id' in criterion or 'parent_tmdb_id' in criterion

            for response in responses:
                subtitle = self.subtitle_class.from_response(
                    response,
                    imdb_match=imdb_match,
                    tmdb_match=tmdb_match,
                )
                # some criteria are redundant, skip the duplicates
                if subtitle.id in seen:
                    continue
                seen.add(subtitle.id)
                logger.debug('Found subtitle %r', subtitle)
                subtitles.append(subtitle)

        # filter out the machine translated subtitles
        if not self.allow_machine_generated:  # pragma: no branch
            subtitles = [s for s in subtitles if not s.machine_translated]

        # sort by download count
        if sort_by_download_count:  # pragma: no branch
            subtitles = sorted(subtitles, key=lambda s: s.download_count or -1, reverse=True)

        return subtitles

    @override
    async def list_subtitles(self, video: Video, languages: Set[Language]) -> list[OpenSubtitlesComSubtitle]:
        """List all the subtitles for the video."""
        query = season = episode = None
        if isinstance(video, Episode):
            query = video.series
            season = video.season
            episode = video.episode
        elif isinstance(video, Movie):  # pragma: no branch
            query = video.title

        return await self.query(
            languages,
            moviehash=video.hashes.get('opensubtitles'),
            imdb_id=video.external_ids.get('imdb_id'),
            tmdb_id=video.external_ids.get('tmdb_id'),
            show_imdb_id=video.external_ids.get('series_imdb_id'),
            show_tmdb_id=video.external_ids.get('series_tmdb_id'),
            query=query,
            season=season,
            episode=episode,
            sort_by_download_count=True,
        )

    # ------------------------------------------------------------------
    # download
    # ------------------------------------------------------------------

    async def download_subtitle(self, subtitle: OpenSubtitlesComSubtitle) -> None:
        """Download the content of the subtitle."""
        logger.info('Downloading subtitle %r', subtitle)

        body = {
            'file_id': subtitle.file_id,
            'file_name': subtitle.file_name,
            'sub_format': self.subtitle_format,
        }
        response = await self._request('POST', 'download', json=body, authenticated=True)

        if any(k not in response for k in ('link', 'remaining')):  # pragma: no cover
            logger.debug('Unable to download subtitle, no link returned by the provider')
            return

        remaining = int(response['remaining'])
        if remaining <= 0:  # pragma: no cover
            reset_time = response.get('reset_time_utc')
            if reset_time:
                logger.error('download quota exceeded, quota reset on %s UTC', reset_time)
            else:
                logger.error('download quota exceeded')
            raise DownloadLimitReached

        content = await self._download_link(response['link'])
        if not content:  # pragma: no cover
            # the provider answers '304 Not Modified' with an empty body,
            # which is not an error status
            logger.debug('Unable to download subtitle. No data returned from provider')
            return

        subtitle.set_content(content)

    async def _download_link(self, link: str) -> bytes:
        """Fetch the subtitle content from the temporary download link.

        The link points to a CDN, not to the API: no API key and no token are sent.
        """
        if self._semaphore is None:  # pragma: no cover
            raise NotInitializedProviderError

        async with (
            self._semaphore,
            self.session.get(
                link,
                headers={'User-Agent': self.user_agent},
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as response,
        ):
            check_status(response.status, response.reason)
            return await response.read()


class OpenSubtitlesComVipSubtitle(OpenSubtitlesComSubtitle):
    """OpenSubtitles.com VIP Subtitle."""

    provider_name: ClassVar[str] = 'opensubtitlescomvip'


class OpenSubtitlesComVipProvider(OpenSubtitlesComProvider):
    """OpenSubtitles.com VIP Provider."""

    server_url: ClassVar[str] = 'https://vip-api.opensubtitles.com/api/v1/'
    subtitle_class: ClassVar = OpenSubtitlesComVipSubtitle


class OpenSubtitlesComError(ProviderError):
    """Base class for non-generic :class:`OpenSubtitlesComProvider` exceptions."""

    pass


class Unauthorized(OpenSubtitlesComError, AuthenticationError):
    """Exception raised when status is '401 Unauthorized'."""

    pass


class NoSession(OpenSubtitlesComError, AuthenticationError):
    """Exception raised when status is '406 No session'."""

    pass


class DownloadLimitReached(OpenSubtitlesComError, DownloadLimitExceeded):
    """Exception raised when status is '407 Download limit reached'."""

    pass


class InvalidImdbid(OpenSubtitlesComError):
    """Exception raised when status is '413 Invalid ImdbID'."""

    pass


class UnknownUserAgent(OpenSubtitlesComError, AuthenticationError):
    """Exception raised when status is '414 Unknown User Agent'."""

    pass


class DisabledUserAgent(OpenSubtitlesComError, AuthenticationError):
    """Exception raised when status is '415 Disabled user agent'."""

    pass


def check_status(status: int, reason: str | None = None) -> None:
    """Raise the exception matching the HTTP status of an OpenSubtitles.com response.

    :param int status: the HTTP status code.
    :param str reason: the HTTP reason phrase, used as error message.
    :raises: :class:`OpenSubtitlesComError`
    """
    if status == 401:  # pragma: no cover
        raise Unauthorized(reason)
    if status == 406:  # pragma: no cover
        raise NoSession
    if status == 407:  # pragma: no cover
        raise DownloadLimitReached
    if status == 413:  # pragma: no cover
        raise InvalidImdbid
    if status == 414:  # pragma: no cover
        raise UnknownUserAgent
    if status == 415:  # pragma: no cover
        raise DisabledUserAgent
    if status == 503:  # pragma: no cover
        raise ServiceUnavailable
    if status != 200:
        raise OpenSubtitlesComError(reason)
