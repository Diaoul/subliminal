"""Refine the :class:`~subliminal.video.Video` object by searching on TheTVDB."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Callable, ClassVar, TypeVar, cast

import guessit  # type: ignore[import-untyped]
import requests
from babelfish import Country  # type: ignore[import-untyped]

from subliminal import __short_version__
from subliminal.cache import REFINER_EXPIRATION_TIME, region
from subliminal.utils import decorate_imdb_id, sanitize, sanitize_id
from subliminal.video import Episode, Video

C = TypeVar('C', bound=Callable)


logger = logging.getLogger(__name__)

#: TheTVDB subliminal API key
TVDB_API_KEY = '5EC930FB90DA1ADA'

series_re = re.compile(r'^(?P<series>.*?)(?: \((?:(?P<year>\d{4})|(?P<country>[A-Z]{2}))\))?$')


def requires_auth(func: C) -> C:
    """Decorator for :class:`TVDBClient` methods that require authentication."""

    @wraps(func)
    def wrapper(self: TVDBClient, *args: Any, **kwargs: Any) -> Any:
        if self.token is None or self.token_expired:
            self.login()
        elif self.token_needs_refresh:
            self.refresh_token()
        return func(self, *args, **kwargs)

    return cast('C', wrapper)


class TVDBClient:
    """TVDB REST API Client.

    :param str apikey: API key to use.
    :param str username: username to use.
    :param str password: password to use.
    :param str language: language of the responses.
    :param session: session object to use.
    :type session: :class:`requests.sessions.Session` or compatible.
    :param dict headers: additional headers.
    :param int timeout: timeout for the requests.

    """

    #: Base URL of the API
    base_url: ClassVar[str] = 'https://api.thetvdb.com'

    #: User agent
    user_agent: ClassVar[str] = f'Subliminal/{__short_version__}'

    #: Token lifespan
    token_lifespan: ClassVar[timedelta] = timedelta(hours=1)

    #: API version
    apiversion: ClassVar[int] = 1

    #: Minimum token age before a :meth:`refresh_token` is triggered
    refresh_token_every: ClassVar[timedelta] = timedelta(minutes=30)

    #: API key
    _apikey: str

    #: Username
    username: str | None

    #: Password
    password: str | None

    #: Last token acquisition date
    token_date: datetime

    #: Session for the requests
    session: requests.Session

    #: Session timeout
    timeout: int

    def __init__(
        self,
        apikey: str | None = None,
        username: str | None = None,
        password: str | None = None,
        language: str = 'en',
        session: requests.Session | None = None,
        headers: dict | None = None,
        timeout: int = 10,
    ) -> None:
        self._apikey = apikey or TVDB_API_KEY
        self.username = username
        self.password = password

        self.token_date = datetime.now(timezone.utc) - self.token_lifespan
        self.timeout = timeout

        #: Session for the requests
        self.session = session if session is not None else requests.Session()
        self.session.headers['User-Agent'] = self.user_agent
        self.session.headers.update(headers or {})
        self.session.headers['Content-Type'] = 'application/json'
        self.session.headers['Accept-Language'] = language

    @property
    def language(self) -> str:
        """Header language of the response."""
        return str(self.session.headers['Accept-Language'])

    @language.setter
    def language(self, value: str) -> None:
        self.session.headers['Accept-Language'] = value

    @property
    def token(self) -> str | None:
        """Authentication token."""
        if 'Authorization' not in self.session.headers:
            return None
        return str(self.session.headers['Authorization'][7:])

    @property
    def token_expired(self) -> bool:
        """Check if the token expired."""
        return datetime.now(timezone.utc) - self.token_date >= self.token_lifespan

    @property
    def token_needs_refresh(self) -> bool:
        """Check if the token needs to be refreshed."""
        return datetime.now(timezone.utc) - self.token_date > self.refresh_token_every

    def login(self) -> None:
        """Login."""
        # perform the request
        data = {'apikey': self.apikey, 'username': self.username, 'password': self.password}
        r = self.session.post(self.base_url + '/login', json=data, timeout=self.timeout)
        r.raise_for_status()

        # set the Authorization header
        self.session.headers['Authorization'] = 'Bearer ' + r.json()['token']

        # update token_date
        self.token_date = datetime.now(timezone.utc)

    def refresh_token(self) -> None:
        """Refresh token."""
        # perform the request
        r = self.session.get(self.base_url + '/refresh_token', timeout=self.timeout)
        r.raise_for_status()

        # set the Authorization header
        self.session.headers['Authorization'] = 'Bearer ' + r.json()['token']

        # update token_date
        self.token_date = datetime.now(timezone.utc)

    @region.cache_on_arguments(expiration_time=REFINER_EXPIRATION_TIME)
    @requires_auth
    def search_series(self, name: str, imdb_id: str | None = None, zap2it_id: str | None = None) -> dict[str, Any]:
        """Search series.

        :param str name: name of the series.
        :param str imdb_id: the IMDB id of the series.
        :param str zap2it_id: the Zap2it id of the series.
        :return: the search results.
        :rtype: list

        """
        # perform the request
        params = {'name': name}
        if imdb_id is not None:
            params['imdbId'] = imdb_id
        if zap2it_id is not None:
            params['zap2itId'] = zap2it_id
        r = self.session.get(self.base_url + '/search/series', params=params, timeout=self.timeout)
        if r.status_code == 404:
            return {}
        r.raise_for_status()

        return cast('dict', r.json()['data'])

    @requires_auth
    def query_series_episodes(
        self,
        series_id: int,
        absolute_number: int | None = None,
        aired_season: int | None = None,
        aired_episode: int | None = None,
        dvd_season: int | None = None,
        dvd_episode: int | None = None,
        imdb_id: str | None = None,
        page: int = 1,
    ) -> dict[str, Any]:
        """Query series episodes."""
        # perform the request
        params = {
            'absoluteNumber': absolute_number,
            'airedSeason': aired_season,
            'airedEpisode': aired_episode,
            'dvdSeason': dvd_season,
            'dvdEpisode': dvd_episode,
            'imdbId': imdb_id,
            'page': page,
        }
        r = self.session.get(
            self.base_url + f'/series/{series_id:d}/episodes/query',
            params=params,
            timeout=self.timeout,
        )
        if r.status_code == 404:
            return {}
        r.raise_for_status()

        return cast('dict', r.json())

    @region.cache_on_arguments(expiration_time=REFINER_EXPIRATION_TIME)
    @requires_auth
    def get_series(self, series_id: int) -> dict[str, Any]:
        """Get series.

        :param int series_id: id of the series.
        :return: the series data.
        :rtype: dict

        """
        # perform the request
        r = self.session.get(self.base_url + f'/series/{series_id:d}', timeout=self.timeout)
        if r.status_code == 404:
            return {}
        r.raise_for_status()

        return cast('dict', r.json()['data'])

    @region.cache_on_arguments(expiration_time=REFINER_EXPIRATION_TIME)
    @requires_auth
    def get_episode(self, episode_id: int) -> dict[str, Any]:
        """Get episode.

        :param int episode_id: id of the episode.
        :return: the episode data.
        :rtype: dict
        """
        # perform the request
        r = self.session.get(self.base_url + f'/episodes/{episode_id:d}', timeout=self.timeout)
        if r.status_code == 404:
            return {}
        r.raise_for_status()

        return cast('dict', r.json()['data'])

    @region.cache_on_arguments(expiration_time=REFINER_EXPIRATION_TIME)
    @requires_auth
    def get_series_episodes(self, series_id: int, page: int = 1) -> dict[str, Any]:
        """Get all the episodes of a series.

        :param int series_id: id of the series.
        :param int page: the page number.
        :return: the data for all the episodes.
        :rtype: dict

        """
        # perform the request
        params = {'page': page}
        r = self.session.get(self.base_url + f'/series/{series_id:d}/episodes', params=params, timeout=self.timeout)
        if r.status_code == 404:
            return {}
        r.raise_for_status()

        return cast('dict', r.json())

    @region.cache_on_arguments(expiration_time=REFINER_EXPIRATION_TIME)
    @requires_auth
    def get_series_episode(self, series_id: int, season: int, episode: int) -> dict[str, Any]:
        """Get an episode of a series.

        :param int series_id: id of the series.
        :param int season: season number of the episode.
        :param int episode: episode number of the episode.
        :return: the episode data.
        :rtype: dict

        """
        result = self.query_series_episodes(series_id, aired_season=season, aired_episode=episode)
        if not result:
            return {}
        return self.get_episode(result['data'][0]['id'])  # type: ignore[no-any-return]

    @region.cache_on_arguments(expiration_time=REFINER_EXPIRATION_TIME)
    @requires_auth
    def get_series_actors(self, series_id: int) -> list[dict]:
        """Get series actors.

        :param int series_id: id of the series.
        :return: the actors data.
        :rtype: dict

        """
        # perform the request
        r = self.session.get(self.base_url + f'/series/{series_id:d}/actors', timeout=self.timeout)
        if r.status_code == 404:
            return []
        r.raise_for_status()

        return cast('list', r.json()['data'])

    @property
    def apikey(self) -> str:
        """API key for search."""
        return self._apikey

    @apikey.setter
    def apikey(self, value: str) -> None:
        # early return if the API key is unchanged
        if value == self._apikey:
            return
        self._apikey = value
        # invalidate the token
        if 'Authorization' in self.session.headers:
            del self.session.headers['Authorization']


#: Default client
tvdb_client = TVDBClient()

#: Configure guessit in order to use GuessitCountryConverter
guessit.api.configure()


def refine(video: Video, *, apikey: str | None = None, force: bool = False, **kwargs: Any) -> Video:
    """Refine a video by searching `TheTVDB <https://thetvdb.com/>`_.

    .. note::

        This refiner only work for instances of :class:`~subliminal.video.Episode`.

    Several attributes can be found:

      * :attr:`~subliminal.video.Episode.series`
      * :attr:`~subliminal.video.Episode.year`
      * :attr:`~subliminal.video.Episode.series_imdb_id`
      * :attr:`~subliminal.video.Episode.series_tvdb_id`
      * :attr:`~subliminal.video.Episode.title`
      * :attr:`~subliminal.video.Video.imdb_id`
      * :attr:`~subliminal.video.Episode.tvdb_id`

    :param Video video: the Video to refine.
    :param (str | None) apikey: a personal API key to use TheTVDB.
    :param bool force: if True, refine even if both the IMDB ids of the series and
        of the episodes are known for an Episode.

    """
    # only deal with Episode videos
    if not isinstance(video, Episode):
        logger.error('Cannot refine movies')
        return video

    # exit if the information is complete
    if not force and video.series_tvdb_id and video.tvdb_id:
        logger.debug('No need to search, TheTVDB ids already exist for the video.')
        return video

    # update the API key
    if apikey is not None:
        tvdb_client.apikey = apikey

    # search the series
    logger.info('Searching series %r', video.series)
    results = tvdb_client.search_series(video.series.lower())
    if not results:
        logger.warning('No results for series')
        return video
    logger.debug('Found %d results', len(results))

    # search for exact matches
    matching_results = []
    for result in results:
        matching_result = {}

        # use seriesName and aliases
        original_series_name = result['seriesName']
        series_names = [original_series_name, *result['aliases']]

        # parse the original series as series + year or country
        series_match = series_re.match(original_series_name)
        if not series_match:  # pragma: no-cover
            logger.debug('Discarding series %r, cannot match to regex %r', original_series_name, series_re)
            continue
        original_match = series_match.groupdict()

        # parse series year
        series_year = None
        if result['firstAired']:
            first_aired = datetime.strptime(result['firstAired'], '%Y-%m-%d').replace(tzinfo=timezone.utc)
            series_year = first_aired.year

        # discard mismatches on year
        if video.year and series_year and video.year != series_year:
            logger.debug('Discarding series %r mismatch on year %d', result['seriesName'], series_year)
            continue

        # iterate over series names
        for series_name in series_names:
            # parse as series, year and country
            series_match = series_re.match(series_name)
            if not series_match:  # pragma: no-cover
                logger.debug('Discarding series name %r, cannot match to regex %r', series_name, series_re)
                continue

            series, year, country = series_match.groups()
            if year:
                year = int(year)

            if country:
                country = Country.fromguessit(country)

            # discard mismatches on year
            if year and (video.original_series or video.year != year):
                logger.debug('Discarding series name %r mismatch on year %d', series, year)
                continue

            # discard mismatches on country
            if video.country and video.country != country:
                logger.debug('Discarding series name %r mismatch on country %r', series, country)
                continue

            # match on sanitized series name
            if sanitize(series) == sanitize(video.series):
                logger.debug('Found exact match on series %r', series_name)
                matching_result['match'] = {
                    'series': original_match.get('series', series),
                    'year': series_year or year,
                    'country': country,
                    'original_series': original_match.get('year') is None and country is None,
                }
                break

        # add the result on match
        if matching_result:
            matching_result['data'] = result
            matching_results.append(matching_result)

    # exit if we don't have exactly 1 matching result
    if not matching_results:
        logger.error('No matching series found')
        return video
    if len(matching_results) > 1:
        logger.error('Multiple matches found')
        return video

    # get the series
    matching_result = matching_results[0]
    series = tvdb_client.get_series(matching_result['data']['id'])

    # add series information
    logger.debug('Found series %r', series)
    video.series = str(matching_result['match']['series'])
    video.alternative_series.extend(series['aliases'])
    video.year = int_or_none(matching_result['match']['year'])
    video.country = matching_result['match']['country']
    video.original_series = bool(matching_result['match']['original_series'])
    video.series_tvdb_id = sanitize_id(series['id'])
    video.series_imdb_id = decorate_imdb_id(sanitize_id(series['imdbId'] or None))

    # get the episode
    logger.info('Getting series episode %dx%d', video.season, video.episode)
    episode = tvdb_client.get_series_episode(video.series_tvdb_id, video.season, video.episode)
    if not episode:
        logger.warning('No results for episode')
        return video

    # add episode information
    logger.debug('Found episode %r', episode)
    video.tvdb_id = sanitize_id(episode['id'])
    video.title = episode['episodeName'] or None
    video.imdb_id = decorate_imdb_id(sanitize_id(episode['imdbId'] or None))

    return video


def int_or_none(value: Any) -> int | None:
    """Convert to int or None."""
    return None if value is None else int(value)
