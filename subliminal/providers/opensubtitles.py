"""Provider for Opensubtitles.org."""

from __future__ import annotations

import base64
import contextlib
import logging
import os
import re
import zlib
from typing import TYPE_CHECKING, Any, ClassVar
from xmlrpc.client import ServerProxy

from babelfish import Language, language_converters  # type: ignore[import-untyped]
from guessit import guessit  # type: ignore[import-untyped]

from subliminal.exceptions import (
    AuthenticationError,
    ConfigurationError,
    DownloadLimitExceeded,
    ProviderError,
    ServiceUnavailable,
)
from subliminal.matches import guess_matches
from subliminal.subtitle import Subtitle, fix_line_ending
from subliminal.utils import decorate_imdb_id, sanitize_id
from subliminal.video import Episode, Movie, Video

from . import Provider, TimeoutSafeTransport

if TYPE_CHECKING:
    from collections.abc import Set

logger = logging.getLogger(__name__)

with contextlib.suppress(ValueError, KeyError):
    # Delete entry from babelfish, if it was defined
    language_converters.internal_converters.remove(
        'opensubtitles = babelfish.converters.opensubtitles:OpenSubtitlesConverter'
    )
    del language_converters.converters['opensubtitles']
    # Register subliminal version
    language_converters.register('opensubtitles = subliminal.converters.opensubtitles:OpenSubtitlesConverter')


class OpenSubtitlesSubtitle(Subtitle):
    """OpenSubtitles Subtitle."""

    provider_name: ClassVar[str] = 'opensubtitles'
    series_re: re.Pattern = re.compile(r'^"(?P<series_name>.*)" (?P<series_title>.*)$')

    matched_by: str | None
    movie_kind: str | None
    moviehash: str | None
    movie_name: str | None
    movie_release_name: str | None
    movie_year: int | None
    movie_imdb_id: str | None
    series_season: int | None
    series_episode: int | None
    filename: str

    def __init__(
        self,
        language: Language,
        subtitle_id: str,
        *,
        hearing_impaired: bool = False,
        page_link: str | None = None,
        matched_by: str | None = None,
        movie_kind: str | None = None,
        moviehash: str | None = None,
        movie_name: str | None = None,
        movie_release_name: str | None = None,
        movie_year: int | None = None,
        movie_imdb_id: str | None = None,
        series_season: int | None = None,
        series_episode: int | None = None,
        filename: str = '',
        encoding: str | None = None,
    ) -> None:
        super().__init__(
            language,
            subtitle_id,
            hearing_impaired=hearing_impaired,
            page_link=page_link,
            encoding=encoding,
        )
        self.matched_by = matched_by
        self.movie_kind = movie_kind
        self.moviehash = moviehash
        self.movie_name = movie_name
        self.movie_release_name = movie_release_name
        self.movie_year = movie_year
        self.movie_imdb_id = movie_imdb_id
        self.series_season = series_season
        self.series_episode = series_episode
        self.filename = filename

    @property
    def info(self) -> str:
        """Information about the subtitle."""
        if not self.filename and not self.movie_release_name:
            return self.id
        if self.movie_release_name and len(self.movie_release_name) > len(self.filename):
            return self.movie_release_name
        return self.filename

    @property
    def series_name(self) -> str:
        """The series name matched from `movie_name`."""
        m = self.series_re.match(self.movie_name)
        if m:
            return str(m.group('series_name'))
        return ''

    @property
    def series_title(self) -> str:
        """The series title matched from `movie_name`."""
        m = self.series_re.match(self.movie_name)
        if m:
            return str(m.group('series_title'))
        return ''

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
                'title': self.series_name if self.movie_kind == 'episode' else self.movie_name,
                'episode_title': self.series_title if self.movie_kind == 'episode' else None,
                'year': self.movie_year,
                'season': self.series_season,
                'episode': self.series_episode,
            },
        )

        # tag
        if self.matched_by == 'tag' and (not video.imdb_id or self.movie_imdb_id == video.imdb_id):
            if self.movie_kind == 'episode':
                matches |= {'series', 'year', 'season', 'episode'}
            elif self.movie_kind == 'movie':
                matches |= {'title', 'year'}

        # guess
        matches |= guess_matches(video, guessit(self.movie_release_name, {'type': self.movie_kind}))
        matches |= guess_matches(video, guessit(self.filename, {'type': self.movie_kind}))

        # moviehash
        if 'opensubtitles' in video.hashes and self.moviehash == video.hashes['opensubtitles']:
            if self.movie_kind == 'movie' and 'title' in matches:  # noqa: SIM114
                matches.add('hash')
            elif self.movie_kind == 'episode' and 'series' in matches and 'season' in matches and 'episode' in matches:
                matches.add('hash')
            else:
                logger.debug('Match on hash discarded')

        # imdb_id
        if video.imdb_id and self.movie_imdb_id == video.imdb_id:
            matches.add('imdb_id')

        return matches


class OpenSubtitlesProvider(Provider):
    """OpenSubtitles Provider.

    :param str username: username.
    :param str password: password.

    """

    languages: ClassVar[Set[Language]] = {
        Language.fromopensubtitles(lang) for lang in language_converters['opensubtitles'].codes
    }
    subtitle_class: ClassVar = OpenSubtitlesSubtitle

    server_url: ClassVar[str] = 'https://api.opensubtitles.org/xml-rpc'
    # user_agent = 'subliminal v%s' % __short_version__
    user_agent: str = 'VLSub 0.11.1'

    username: str | None
    password: str | None
    token: str | None
    server: ServerProxy

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        *,
        timeout: int = 10,
    ) -> None:
        transport = TimeoutSafeTransport(timeout=timeout, user_agent='VLSub')
        self.server = ServerProxy(self.server_url, transport)
        if any((username, password)) and not all((username, password)):
            msg = 'Username and password must be specified'
            raise ConfigurationError(msg)
        # None values not allowed for logging in, so replace it by ''
        self.username = username or ''
        self.password = password or ''
        self.token = None

    def initialize(self) -> None:
        """Initialize the provider."""
        logger.info('Logging in')
        response = checked(self.server.LogIn(self.username, self.password, 'eng', self.user_agent))  # type: ignore[arg-type]
        self.token = str(response['token'])
        logger.debug('Logged in with token %r', self.token)

    def terminate(self) -> None:
        """Terminate the provider."""
        logger.info('Logging out')
        checked(self.server.LogOut(self.token))  # type: ignore[arg-type]
        self.server.close()
        self.token = None
        logger.debug('Logged out')

    def no_operation(self) -> None:
        """No-operation on the server."""
        logger.debug('No operation')
        checked(self.server.NoOperation(self.token))  # type: ignore[arg-type]

    def query(
        self,
        languages: Set[Language],
        *,
        moviehash: str | None = None,
        size: int | None = None,
        imdb_id: str | None = None,
        query: str | None = None,
        season: int | None = None,
        episode: int | None = None,
        tag: str | None = None,
    ) -> list[OpenSubtitlesSubtitle]:
        """Query the server and return all the data."""
        # fill the search criteria
        criteria: list[dict[str, Any]] = []
        if moviehash and size:
            criteria.append({'moviehash': moviehash, 'moviebytesize': str(size)})
        if imdb_id:
            if season and episode:
                criteria.append({'imdbid': sanitize_id(imdb_id), 'season': season, 'episode': episode})
            else:
                criteria.append({'imdbid': sanitize_id(imdb_id)})
        if tag:
            criteria.append({'tag': tag})
        if query and season and episode:
            criteria.append({'query': query.replace("'", ''), 'season': season, 'episode': episode})
        elif query:
            criteria.append({'query': query.replace("'", '')})
        if not criteria:
            msg = 'Not enough information'
            raise ValueError(msg)

        # add the language
        for criterion in criteria:
            criterion['sublanguageid'] = ','.join(sorted(lang.opensubtitles for lang in languages))

        # query the server
        logger.info('Searching subtitles %r', criteria)
        response = checked(self.server.SearchSubtitles(self.token, criteria))  # type: ignore[arg-type]
        subtitles: list[OpenSubtitlesSubtitle] = []

        # exit if no data
        if not response['data']:
            logger.debug('No subtitles found')
            return subtitles

        # loop over subtitle items
        for subtitle_item in response['data']:
            # read the item
            language = Language.fromopensubtitles(subtitle_item['SubLanguageID'])
            hearing_impaired = bool(int(subtitle_item['SubHearingImpaired']))
            page_link = subtitle_item['SubtitlesLink']
            subtitle_id = int(subtitle_item['IDSubtitleFile'])
            matched_by = subtitle_item['MatchedBy']
            movie_kind = subtitle_item['MovieKind']
            moviehash = subtitle_item['MovieHash']
            movie_name = subtitle_item['MovieName']
            movie_release_name = subtitle_item['MovieReleaseName']
            movie_year = int(subtitle_item['MovieYear']) if subtitle_item['MovieYear'] else None
            movie_imdb_id = decorate_imdb_id(subtitle_item['IDMovieImdb'])
            series_season = int(subtitle_item['SeriesSeason']) if subtitle_item['SeriesSeason'] else None
            series_episode = int(subtitle_item['SeriesEpisode']) if subtitle_item['SeriesEpisode'] else None
            filename = subtitle_item['SubFileName']
            encoding = subtitle_item.get('SubEncoding') or None

            subtitle = self.subtitle_class(
                language=language,
                subtitle_id=subtitle_id,
                hearing_impaired=hearing_impaired,
                page_link=page_link,
                matched_by=matched_by,
                movie_kind=movie_kind,
                moviehash=moviehash,
                movie_name=movie_name,
                movie_release_name=movie_release_name,
                movie_year=movie_year,
                movie_imdb_id=movie_imdb_id,
                series_season=series_season,
                series_episode=series_episode,
                filename=filename,
                encoding=encoding,
            )
            logger.debug('Found subtitle %r by %s', subtitle, matched_by)
            subtitles.append(subtitle)

        return subtitles

    def list_subtitles(self, video: Video, languages: Set[Language]) -> list[OpenSubtitlesSubtitle]:
        """List all the subtitles for the video."""
        season = episode = None
        if isinstance(video, Episode):
            query = video.series
            season = video.season
            episode = video.episode
        elif isinstance(video, Movie):
            query = video.title
        else:
            return []

        return self.query(
            languages,
            moviehash=video.hashes.get('opensubtitles'),
            size=video.size,
            imdb_id=video.imdb_id,
            query=query,
            season=season,
            episode=episode,
            tag=os.path.basename(video.name),
        )

    def download_subtitle(self, subtitle: OpenSubtitlesSubtitle) -> None:
        """Download the content of the subtitle."""
        logger.info('Downloading subtitle %r', subtitle)
        response = checked(self.server.DownloadSubtitles(self.token, [str(subtitle.subtitle_id)]))  # type: ignore[arg-type]
        subtitle.content = fix_line_ending(zlib.decompress(base64.b64decode(response['data'][0]['data']), 47))


class OpenSubtitlesVipSubtitle(OpenSubtitlesSubtitle):
    """OpenSubtitles Subtitle."""

    provider_name = 'opensubtitlesvip'


class OpenSubtitlesVipProvider(OpenSubtitlesProvider):
    """OpenSubtitles Provider using VIP url."""

    server_url = 'https://vip-api.opensubtitles.org/xml-rpc'
    subtitle_class = OpenSubtitlesVipSubtitle


class OpenSubtitlesError(ProviderError):
    """Base class for non-generic :class:`OpenSubtitlesProvider` exceptions."""

    pass


class Unauthorized(OpenSubtitlesError, AuthenticationError):
    """Exception raised when status is '401 Unauthorized'."""

    pass


class NoSession(OpenSubtitlesError, AuthenticationError):
    """Exception raised when status is '406 No session'."""

    pass


class DownloadLimitReached(OpenSubtitlesError, DownloadLimitExceeded):
    """Exception raised when status is '407 Download limit reached'."""

    pass


class InvalidImdbid(OpenSubtitlesError):
    """Exception raised when status is '413 Invalid ImdbID'."""

    pass


class UnknownUserAgent(OpenSubtitlesError, AuthenticationError):
    """Exception raised when status is '414 Unknown User Agent'."""

    pass


class DisabledUserAgent(OpenSubtitlesError, AuthenticationError):
    """Exception raised when status is '415 Disabled user agent'."""

    pass


def checked(response: dict[str, Any]) -> dict[str, Any]:
    """Check a response status before returning it.

    :param response: a response from a XMLRPC call to OpenSubtitles.
    :return: the response.
    :raise: :class:`OpenSubtitlesError`

    """
    status_code = int(response['status'][:3])
    if status_code == 401:
        raise Unauthorized
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
        raise OpenSubtitlesError(response['status'])

    return response
