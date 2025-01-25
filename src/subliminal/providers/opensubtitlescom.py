"""Provider for Opensubtitles.com."""

from __future__ import annotations

import contextlib
import logging
import time
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, ClassVar, TypeVar, cast

from babelfish import Language, language_converters  # type: ignore[import-untyped]
from dogpile.cache.api import NO_VALUE
from guessit import guessit  # type: ignore[import-untyped]
from requests import Response, Session

from subliminal import __short_version__
from subliminal.cache import region
from subliminal.exceptions import (
    AuthenticationError,
    ConfigurationError,
    DownloadLimitExceeded,
    NotInitializedProviderError,
    ProviderError,
    ServiceUnavailable,
)
from subliminal.matches import guess_matches
from subliminal.subtitle import Subtitle, fix_line_ending
from subliminal.video import Episode, Movie, Video

from . import Provider

if TYPE_CHECKING:
    from collections.abc import Mapping, Set

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


opensubtitlescom_languages = {
    Language('por', 'BR'),
    Language('srp', 'ME'),
    Language('zho', 'TW'),
    Language('zho', 'US'),
} | {
    Language(lang)
    for lang in [
        'afr',
        'ara',
        'arg',
        'ast',
        'bel',
        'ben',
        'bos',
        'bre',
        'bul',
        'cat',
        'ces',
        'dan',
        'deu',
        'ell',
        'eng',
        'epo',
        'est',
        'eus',
        'fas',
        'fin',
        'fra',
        'glg',
        'heb',
        'hin',
        'hrv',
        'hun',
        'hye',
        'ind',
        'isl',
        'ita',
        'jpn',
        'kat',
        'kaz',
        'khm',
        'kor',
        'lav',
        'lit',
        'ltz',
        'mal',
        'mkd',
        'mni',
        'mon',
        'msa',
        'mya',
        'nld',
        'nor',
        'oci',
        'pol',
        'ron',
        'rus',
        'sin',
        'slk',
        'slv',
        'spa',
        'sqi',
        'srp',
        'swa',
        'swe',
        'syr',
        'tam',
        'tel',
        'tgl',
        'tha',
        'tur',
        'ukr',
        'urd',
        'uzb',
        'vie',
    ]
}


def sanitize_id(id_: int | str | None) -> int | None:
    """Sanitize the IMDB (or other) id and transform it to a string (without leading 'tt' or zeroes)."""
    if id_ is None:
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
        subtitle_id = str(int(response.get('id')))  # type: ignore[arg-type]

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
        file_id = int(srt_file.get('file_id'))  # type: ignore[arg-type]
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
    def info(self) -> str:
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
        matches |= guess_matches(video, guessit(self.release, {'type': self.movie_kind}))
        matches |= guess_matches(video, guessit(self.file_name, {'type': self.movie_kind}))

        # imdb_id
        if self.imdb_match:
            matches.add('imdb_id')

        # tmdb_id
        if self.tmdb_match:
            matches.add('tmdb_id')

        # hash match
        if self.moviehash_match:
            matches.add('hash')

        return matches


def requires_auth(func: C) -> C:
    """Decorator for :class:`OpenSubtitlesComProvider` methods that require authentication."""

    @wraps(func)
    def wrapper(self: OpenSubtitlesComProvider, *args: Any, **kwargs: Any) -> Any:
        if not self.check_token():
            # token expired
            self.login()

            if not self.check_token():
                msg = 'Cannot authenticate with username and password'
                raise AuthenticationError(msg)

        return func(self, *args, **kwargs)

    return cast(C, wrapper)


class OpenSubtitlesComProvider(Provider):
    """OpenSubtitles.com Provider.

    :param str username: username.
    :param str password: password.

    """

    server_url: ClassVar[str] = 'https://api.opensubtitles.com/api/v1/'
    subtitle_class: ClassVar = OpenSubtitlesComSubtitle
    languages: ClassVar[Set[Language]] = opensubtitlescom_languages

    user_agent: str = f'Subliminal v{__short_version__}'
    subtitle_format: str = 'srt'

    username: str | None
    password: str | None
    apikey: str
    timeout: int
    token_expires_at: datetime | None
    session: Session | None

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        *,
        apikey: str | None = None,
        timeout: int = 20,
    ) -> None:
        if any((username, password)) and not all((username, password)):
            msg = 'Username and password must be specified'
            raise ConfigurationError(msg)

        self.username = username
        self.password = password
        self.apikey = apikey or OPENSUBTITLESCOM_API_KEY
        self.timeout = timeout
        self.token_expires_at = None
        self.session = None

    def initialize(self) -> None:
        """Initialize the provider."""
        self.session = Session()
        self.session.headers['User-Agent'] = self.user_agent
        self.session.headers['Api-Key'] = self.apikey
        self.session.headers['Accept'] = '*/*'
        self.session.headers['Content-Type'] = 'application/json'

    def terminate(self) -> None:
        """Terminate the provider."""
        if not self.session:
            raise NotInitializedProviderError

        # logout
        self.logout()

    def check_token(self) -> bool:
        """Check if the token is valid."""
        if not self.session:
            raise NotInitializedProviderError

        # Check token is present
        if self.token_expires_at is not None and self.token is not None:
            if datetime.now(timezone.utc) < self.token_expires_at:
                return True
            del self.token
            self.token_expires_at = None

        # Check cached token
        token = region.get('oscom_token', expiration_time=TOKEN_EXPIRATION_TIME)
        if token is NO_VALUE:
            return False

        # Login was already done, add token to Bearer
        self.session.headers['Authorization'] = 'Bearer ' + str(token)
        return True

    def login(self, *, wait: bool = False) -> None:
        """Login with the POST REST API."""
        if not self.session:
            raise NotInitializedProviderError
        if not self.username or not self.password:
            logger.info('Cannot log in, a username and password must be provided')
            return

        if wait:
            # Wait 1s between calls
            time.sleep(1)

        logger.info('Logging in')
        data = {'username': self.username, 'password': self.password}

        try:
            r = self.session.post(self.server_url + 'login', json=data, timeout=self.timeout)
            r = checked(r)
        except ProviderError:
            # raise error
            logger.exception('An error occurred')
            raise

        ret = r.json()
        token = ret['token']
        if not token:
            logger.debug('Error, the authentication token is empty.')
            return

        # Set cache
        region.set('oscom_token', token)
        # Set token in header
        self.token = token
        self.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=TOKEN_EXPIRATION_TIME)

        logger.debug('Logged in')

    def logout(self) -> None:
        """Logout by closing the Session."""
        if not self.session:
            raise NotInitializedProviderError
        del self.token
        self.session.close()

    @staticmethod
    def reset_token() -> None:
        """Reset the authentication token from the cache."""
        logger.debug('Authentication failed: clearing cache and attempting to login.')
        region.delete('oscom_token')

    @property
    def token(self) -> str | None:
        """Authentication token."""
        if not self.session:
            return None
        if 'Authorization' not in self.session.headers:
            return None
        auth = str(self.session.headers['Authorization'])
        prefix = 'Bearer '
        if auth is None or not auth.startswith(prefix):
            return None
        return auth[len(prefix) :]

    @token.setter
    def token(self, value: str) -> None:
        """Authentication token."""
        if not self.session:
            return
        self.session.headers['Authorization'] = 'Bearer ' + str(value)

    @token.deleter
    def token(self) -> None:
        """Authentication token."""
        if not self.session:
            return
        if 'Authorization' in self.session.headers:
            del self.session.headers['Authorization']

    @requires_auth
    def user_infos(self) -> dict[str, Any]:
        """Return information about the user."""
        if not self.session:
            raise NotInitializedProviderError

        logger.debug('User infos')

        response = self.api_get('infos/user')
        logger.debug(response)
        return response

    def api_post(
        self,
        path: str,
        body: Mapping[str, Any] | None = None,
        *,
        raises: bool = True,
    ) -> dict[str, Any]:
        """Make a POST request to the path, with body."""
        if not self.session:
            raise NotInitializedProviderError

        body = dict(body) if body else {}

        # no need to set the headers, there are set for `self.session`
        try:
            r = self.session.post(self.server_url + path, json=body, timeout=self.timeout)
            r = checked(r)
        except ProviderError:
            logger.exception('An error occurred')
            if raises:
                raise
            return {}

        return r.json()  # type: ignore[no-any-return]

    def api_get(
        self,
        path: str,
        params: Mapping[str, Any] | None = None,
        *,
        raises: bool = True,
    ) -> dict[str, Any]:
        """Make a GET request to the path, with parameters."""
        if not self.session:
            raise NotInitializedProviderError
        # sort dict
        params = dict(sorted(params.items())) if params else {}
        # lowercase, do not transform spaces to "+", because then they become html-encoded
        params = {k.lower(): (v.lower() if isinstance(v, str) else v) for k, v in params.items()}

        # no need to set the headers, there are set for `self.session`
        try:
            r = self.session.get(self.server_url + path, params=params, timeout=self.timeout)
            r = checked(r)
        except ProviderError:
            logger.exception('An error occurred')
            if raises:
                raise
            return {}

        return r.json()  # type: ignore[no-any-return]

    def _search(self, *, page: int = 1, **params: Any) -> list[dict[str, Any]]:
        # query the server
        logger.info('Searching subtitles %r', params)

        # GET request and add page information
        response = self.api_get('subtitles', {'page': page, **params})

        if not response or not response['data']:
            return []

        ret = response['data']

        # retrieve other pages maybe
        if 'total_pages' in response and page < response['total_pages']:
            # missing pages
            ret.extend(self._search(page=page + 1, **params))

        return ret  # type: ignore[no-any-return]

    def _make_query(
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
        """Make a list of query parameters."""
        # fill the search criterion
        criterion: dict[str, Any] = {}
        if moviehash:
            criterion.update({'moviehash': moviehash})

        if imdb_id:
            criterion.update({'imdb_id': sanitize_id(imdb_id)})
            if show_imdb_id:
                criterion.update({'parent_imdb_id': sanitize_id(show_imdb_id)})

        if tmdb_id:
            criterion.update({'tmdb_id': sanitize_id(tmdb_id)})
            if show_tmdb_id:
                criterion.update({'parent_tmdb_id': sanitize_id(show_tmdb_id)})

        if opensubtitles_id:
            criterion.update({'id': opensubtitles_id})

        if query:
            criterion.update({'query': query.replace("'", '')})

        if season and episode:
            criterion.update({'season_number': season, 'episode_number': episode})
        if year:
            criterion.update({'year': year})

        # return a list of criteria
        if not criterion:
            msg = 'Not enough information'
            raise ValueError(msg)

        criteria = [criterion]
        # Add single-term searches to the list of searches.
        # Only if the criterion is a multi-term search.
        if len(criterion) > 1:
            if 'id' in criterion:
                criteria.append({'id': criterion['id']})
            if 'imdb_id' in criterion:
                criteria.append({'imdb_id': criterion['imdb_id']})
            if 'tmdb_id' in criterion:
                criteria.append({'tmdb_id': criterion['tmdb_id']})
            if 'moviehash' in criterion:
                criteria.append({'moviehash': criterion['moviehash']})
            if 'query' in criterion:
                if 'season_number' in criterion and 'episode_number' in criterion:
                    criteria.append(
                        {
                            'query': criterion['query'],
                            'season_number': criterion['season_number'],
                            'episode_number': criterion['episode_number'],
                        }
                    )
                else:
                    criteria.append({'query': criterion['query']})

        return criteria

    def query(
        self,
        languages: Set[Language],
        *,
        allow_machine_translated: bool = False,
        sort_by_download_count: bool = True,
        **kwargs: Any,
    ) -> list[OpenSubtitlesComSubtitle]:
        """Query the server and return all the data."""
        # fill the search criteria
        criteria = self._make_query(**kwargs)

        subtitles: list[OpenSubtitlesComSubtitle] = []

        for criterion in criteria:
            # add the language and query the server
            criterion.update({'languages': ','.join(sorted(lang.opensubtitlescom for lang in languages))})

            # query the server
            responses = self._search(**criterion)

            imdb_match = 'imdb_id' in criterion or 'show_imdb_id' in criterion
            tmdb_match = 'tmdb_id' in criterion or 'show_tmdb_id' in criterion

            # loop over subtitle items
            for response in responses:
                # read single response
                subtitle = self.subtitle_class.from_response(
                    response,
                    imdb_match=imdb_match,
                    tmdb_match=tmdb_match,
                )

                # Some criteria are redundant, so skip duplicates
                # Use set for faster search
                unique_ids = {s.id for s in subtitles}
                if subtitle.id not in unique_ids:
                    logger.debug('Found subtitle %r', subtitle)
                    subtitles.append(subtitle)

        # filter out the machine translated subtitles
        if not allow_machine_translated:
            subtitles = [sub for sub in subtitles if not sub.machine_translated]
        # sort by download_counts
        if sort_by_download_count:
            subtitles = sorted(subtitles, key=lambda s: s.download_count or -1, reverse=True)

        return list(subtitles)

    def list_subtitles(self, video: Video, languages: Set[Language]) -> list[OpenSubtitlesComSubtitle]:
        """List all the subtitles for the video."""
        query = season = episode = None
        if isinstance(video, Episode):
            # TODO: add show_imdb_id and show_tmdb_id
            query = video.series
            season = video.season
            episode = video.episode
        elif isinstance(video, Movie):
            query = video.title

        return self.query(
            languages,
            moviehash=video.hashes.get('opensubtitles'),
            imdb_id=video.imdb_id,
            query=query,
            season=season,
            episode=episode,
            allow_machine_translated=False,
            sort_by_download_count=True,
        )

    @requires_auth
    def download_subtitle(self, subtitle: OpenSubtitlesComSubtitle) -> None:
        """Download the content of the subtitle."""
        if not self.session:
            raise NotInitializedProviderError

        # get the subtitle download link
        logger.info('Downloading subtitle %r', subtitle)
        body = {'file_id': subtitle.file_id, 'file_name': subtitle.file_name, 'sub_format': self.subtitle_format}
        r = self.api_post('download', body)
        if any(k not in r for k in ('link', 'remaining')):
            return

        link = r['link']
        remaining = int(r['remaining'])

        # detect download limit exceeded
        if remaining <= 0:
            if 'reset_time_utc' in r:
                logger.error('download quota exceeded, quota reset on %s UTC', r['reset_time_utc'])
            else:
                logger.error('download quota exceeded')
            raise DownloadLimitReached

        # download the subtitle
        download_response = self.session.get(link, timeout=self.timeout)

        if not download_response.content:
            # Provider returns a status of 304 Not Modified with an empty content
            # raise_for_status won't raise exception for that status code
            logger.debug('Unable to download subtitle. No data returned from provider')
            return

        subtitle.content = fix_line_ending(download_response.content)


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


def checked(response: Response) -> Response:
    """Check a response status before returning it.

    :param response: a response from `requests` call to OpenSubtitlesCom.
    :return: the response.
    :raises: :class:`OpenSubtitlesComError`

    """
    status_code = response.status_code
    if status_code == 401:
        raise Unauthorized(response.reason)
    if status_code == 406:
        raise NoSession
    if status_code == 407:
        raise DownloadLimitReached
    if status_code == 413:
        raise InvalidImdbid
    if status_code == 414:
        raise UnknownUserAgent
    if status_code == 415:
        raise DisabledUserAgent
    if status_code == 503:
        raise ServiceUnavailable
    if status_code != 200:
        raise OpenSubtitlesComError(response.reason)

    return response
