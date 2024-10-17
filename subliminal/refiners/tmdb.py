"""Refine the :class:`~subliminal.video.Video` object by searching on TMDB."""

from __future__ import annotations

import logging
import re
from typing import Any, ClassVar, cast

import requests

from subliminal import __short_version__
from subliminal.cache import REFINER_EXPIRATION_TIME, region
from subliminal.utils import decorate_imdb_id, sanitize, sanitize_id
from subliminal.video import Episode, Movie, Video

logger = logging.getLogger(__name__)

series_re = re.compile(r'^(?P<series>.*?)(?: \((?:(?P<year>\d{4})|(?P<country>[A-Z]{2}))\))?$')


def split_year(data: dict[str, Any], key: str) -> int | None:
    """Found the date from dict and split the year."""
    try:
        return int(data[key].split('-')[0])
    except (ValueError, KeyError, AttributeError):
        logger.exception(f'Cannot extract year from date in {data.get(key)}')
    return None


class TMDBClient:
    """TMDB API Client.

    :param str apikey: API key to use.
    :param session: session object to use.
    :type session: :class:`requests.sessions.Session` or compatible.
    :param dict headers: additional headers.
    :param int timeout: timeout for the requests.

    """

    #: API version
    api_version: ClassVar[int] = 3

    #: Base URL of the API
    base_url: ClassVar[str] = f'https://api.themoviedb.org/{api_version}'

    #: User agent
    user_agent: ClassVar[str] = f'Subliminal/{__short_version__}'

    #: API key
    _apikey: str | None

    #: Session for the requests
    session: requests.Session

    #: Session timeout
    timeout: int

    def __init__(
        self,
        apikey: str | None = None,
        session: requests.Session | None = None,
        headers: dict | None = None,
        timeout: int = 10,
    ) -> None:
        self._apikey = apikey
        self.timeout = timeout

        #: Session for the requests
        self.session = session if session is not None else requests.Session()
        self.session.headers['User-Agent'] = self.user_agent
        self.session.headers.update(headers or {})
        self.session.headers['Content-Type'] = 'application/json'
        self.session.headers['Accept-Language'] = 'en'
        if apikey is not None:
            self.session.params['api_key'] = self.apikey  # type: ignore[index]

    @region.cache_on_arguments(expiration_time=REFINER_EXPIRATION_TIME)
    def search(
        self,
        title: str,
        is_movie: bool,  # noqa: FBT001
        year: int | None = None,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        """Search on TMDB and return a list of results."""
        title = title.replace("'", '')
        title_year = title + (f' ({year})' if year else '')
        category = 'movie' if is_movie else 'tv'

        logger.info('Searching TMDB for %r (%s)', title_year, category)

        params: dict[str, Any] = {'query': title, 'language': 'en-US', 'page': page}
        if year is not None:
            params['year'] = year
        r = self.session.get(self.base_url + f'/search/{category}', params=params)

        r.raise_for_status()
        return cast(list, r.json().get('results'))

    @region.cache_on_arguments(expiration_time=REFINER_EXPIRATION_TIME)
    def get_id(
        self,
        title: str,
        is_movie: bool,  # noqa: FBT001
        year: int | None = None,
        country: str | None = None,
    ) -> int | None:
        """Search on TMDB and return the best matching."""
        results = self.search(title, year=year, is_movie=is_movie)

        title = title.replace("'", '')
        sanitized_title = sanitize(title)
        title_key = 'title' if is_movie else 'name'
        year_key = 'release_date' if is_movie else 'first_air_date'

        # Loosely match if we found only one result, it is a very probable match
        loose_matching = len(results) == 1

        for result in results:
            # match title
            # first try 'title' in result, fallback to 'name'
            res_title = sanitize(result.get(title_key))
            # res_title = sanitize(result.get('title', result.get('name'), None))
            if not loose_matching and res_title != sanitized_title:
                continue

            # match year
            if year is not None:
                match_year = split_year(result, year_key)
                if match_year is None or match_year != year:
                    continue

            # match country
            if not loose_matching and country is not None and 'origin_country' in result:  # noqa: SIM102
                if country.lower() not in [c.lower() for c in result['origin_country']]:
                    continue

            # found a match
            return int(result['id'])

        title_year = title + (f' ({year})' if year else '')
        logger.warning('No match for %r from the %d results', title_year, len(results))
        return None

    @region.cache_on_arguments(expiration_time=REFINER_EXPIRATION_TIME)
    def query(
        self,
        tmdb_id: int,
        is_movie: bool,  # noqa: FBT001
        season: int | None = None,
        episode: int | None = None,
    ) -> dict[str, Any]:
        """Query a movie or series by TMDB id."""
        category = 'movie' if is_movie else 'tv'
        logger.info('Searching for TMDB id %d (%s)', tmdb_id, category)

        # make url path
        path = f'/{category}/{tmdb_id}'
        if season is not None:
            path = f'{path}/season/{season}'
        if episode is not None:
            path = f'{path}/episode/{episode}'

        params: dict[str, Any] = {'append_to_response': 'external_ids'}
        r = self.session.get(self.base_url + path, params=params)
        r.raise_for_status()

        return cast(dict, r.json())

    @region.cache_on_arguments(expiration_time=REFINER_EXPIRATION_TIME)
    def search_movie(
        self,
        title: str,
        year: int | None = None,
        country: str | None = None,
    ) -> dict[str, Any]:
        """Search for series."""
        tmdb_id = self.get_id(title, is_movie=True, year=year, country=country)
        if tmdb_id is None:
            return {}
        res = self.query(tmdb_id, is_movie=True)
        return cast(dict, res)

    @region.cache_on_arguments(expiration_time=REFINER_EXPIRATION_TIME)
    def search_series(
        self,
        series_name: str,
        year: int | None = None,
        country: str | None = None,
    ) -> dict[str, Any]:
        """Search for series."""
        tmdb_id = self.get_id(series_name, is_movie=False, year=year, country=country)
        if tmdb_id is None:
            return {}
        res = self.query(tmdb_id, is_movie=False)
        return cast(dict, res)

    @region.cache_on_arguments(expiration_time=REFINER_EXPIRATION_TIME)
    def search_episode(
        self,
        series_name: str,
        season: int,
        episode: int,
        year: int | None = None,
        country: str | None = None,
    ) -> dict[str, Any]:
        """Search for episode."""
        tmdb_id = self.get_id(series_name, is_movie=False, year=year, country=country)
        if tmdb_id is None:
            return {}
        res = self.query(tmdb_id, is_movie=False, season=season, episode=episode)
        return cast(dict, res)

    @property
    def apikey(self) -> str | None:
        """API key for search."""
        return self._apikey

    @apikey.setter
    def apikey(self, value: str | None) -> None:
        # early return if the API key is unchanged
        if value == self._apikey:
            return
        self._apikey = value
        # update the default session parameters
        if value:
            self.session.params['api_key'] = self.apikey  # type: ignore[index]


def refine_episode(client: TMDBClient, video: Episode, *, force: bool = False, **kwargs: Any) -> None:
    """Refine an Episode by searching `TMDB API <https://api.themoviedb.org>`_."""
    # exit if the information is complete
    if not force and video.series_tmdb_id and video.tmdb_id:
        logger.debug('No need to search, TMDB ids already exist for the video.')
        return

    # search the series id
    country_code = None if video.country is None else str(video.country)
    tmdb_id = client.get_id(video.series, is_movie=False, year=video.year, country=country_code)
    if tmdb_id is None:
        logger.warning('No results for series')
        return

    # search the series
    result_series = client.query(tmdb_id, is_movie=False)
    if not result_series:  # pragma: no-cover
        logger.warning('No results for series')
        return

    # search the episode
    result_episode = client.query(tmdb_id, is_movie=False, season=video.season, episode=video.episode)
    if not result_episode:  # pragma: no-cover
        logger.warning('No results for series')
        return

    # add series information
    logger.debug('Found series %r', result_episode)
    video.series = result_series['name']
    video.year = split_year(result_series, 'first_air_date')
    series_original_name = result_series['original_name']
    if series_original_name != video.series and series_original_name not in video.alternative_series:
        video.alternative_series.append(series_original_name)
    video.series_tmdb_id = sanitize_id(result_series['id'])
    video.series_imdb_id = decorate_imdb_id(
        sanitize_id(result_series['external_ids'].get('imdb_id', video.series_imdb_id))
    )
    video.series_tvdb_id = sanitize_id(result_series['external_ids'].get('tvdb_id', video.series_tvdb_id))

    video.title = result_episode['name']
    video.tmdb_id = sanitize_id(result_episode['id'])
    video.imdb_id = decorate_imdb_id(sanitize_id(result_episode['external_ids'].get('imdb_id', video.imdb_id)))
    video.tvdb_id = sanitize_id(result_episode['external_ids'].get('tvdb_id', video.tvdb_id))


def refine_movie(client: TMDBClient, video: Movie, *, force: bool = False, **kwargs: Any) -> None:
    """Refine a Movie by searching `TMDB API <https://api.themoviedb.org>`_."""
    # exit if the information is complete
    if not force and video.tmdb_id:
        logger.debug('No need to search, TMDB ids already exist for the video.')
        return

    # search the movie
    result = client.search_movie(video.title, year=video.year)
    if not result:
        logger.warning('No results for movie')
        return

    # add movie information
    logger.debug('Found movie %r', result)
    video.title = result['title']
    video.year = split_year(result, 'release_date')
    original_name = result['original_title']
    if original_name != video.title and original_name not in video.alternative_titles:
        video.alternative_titles.append(original_name)
    video.tmdb_id = sanitize_id(result['id'])
    video.imdb_id = decorate_imdb_id(sanitize_id(result['imdb_id']))


#: Default client
tmdb_client = TMDBClient()


def refine(video: Video, *, apikey: str | None = None, force: bool = False, **kwargs: Any) -> Video:
    """Refine a video by searching `TMDB API <https://api.themoviedb.org>`_.

    Several :class:`~subliminal.video.Episode` attributes can be found:

      * :attr:`~subliminal.video.Episode.series`
      * :attr:`~subliminal.video.Episode.year`
      * :attr:`~subliminal.video.Episode.series_tmdb_id`
      * :attr:`~subliminal.video.Episode.tmdb_id`
      * :attr:`~subliminal.video.Episode.series_imdb_id`
      * :attr:`~subliminal.video.Episode.imdb_id`

    Similarly, for a :class:`~subliminal.video.Movie`:

      * :attr:`~subliminal.video.Movie.title`
      * :attr:`~subliminal.video.Movie.year`
      * :attr:`~subliminal.video.Video.tmdb_id`
      * :attr:`~subliminal.video.Video.imdb_id`

    :param Video video: the Video to refine.
    :param (str | None) apikey: a personal API key to use TMDB.
    :param bool force: if True, refine even if TMDB id is already known for a Movie or
        if both the TMDB ids of the series and of the episodes are known for an Episode.

    """
    # update the API key
    if apikey is not None:
        tmdb_client.apikey = apikey
    else:
        logger.info('You must provide an `apikey` for the TMDB refiner, aborting.')
        return video

    # refine for Episode
    if isinstance(video, Episode):
        refine_episode(tmdb_client, video, force=force, **kwargs)

    # refine for Movie
    elif isinstance(video, Movie):
        refine_movie(tmdb_client, video, force=force, **kwargs)

    return video
