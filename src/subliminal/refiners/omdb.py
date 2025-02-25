"""Refine the :class:`~subliminal.video.Video` object by searching on OMDB."""

from __future__ import annotations

import logging
import operator
from typing import TYPE_CHECKING, Any, ClassVar, cast

import requests

from subliminal import __short_version__
from subliminal.cache import REFINER_EXPIRATION_TIME, region
from subliminal.utils import decorate_imdb_id, sanitize_id
from subliminal.video import Episode, Movie, Video

if TYPE_CHECKING:
    from collections.abc import Mapping

logger = logging.getLogger(__name__)

#: OMDB subliminal API key
OMDB_API_KEY = '44d5b275'


def split_year_omdb(string: str) -> int | None:
    """Split the year."""
    try:
        return int(string.split('\u2013')[0].split('-')[0])
    except (ValueError, AttributeError):  # pragma: no cover
        logger.exception(f'Cannot extract year from date in {string!r}')
    return None


class OMDBClient:
    """Client to connect to the OMDB API."""

    base_url: ClassVar[str] = 'https://www.omdbapi.com'
    user_agent: ClassVar[str] = f'Subliminal/{__short_version__}'

    _apikey: str
    timeout: int

    def __init__(
        self,
        apikey: str | None = None,
        version: int = 1,
        session: requests.Session | None = None,
        headers: Mapping[str, Any] | None = None,
        timeout: int = 10,
    ) -> None:
        self._apikey = apikey or OMDB_API_KEY
        self.timeout = timeout

        #: Session for the requests
        self.session = session if session is not None else requests.Session()
        self.session.headers['User-Agent'] = self.user_agent
        self.session.headers.update(headers or {})
        self.session.params['r'] = 'json'  # type: ignore[index]
        self.session.params['v'] = version  # type: ignore[index]
        self.session.params['apikey'] = self.apikey  # type: ignore[index]

    def get(
        self,
        *,
        id: int | None = None,  # noqa: A002
        title: str | None = None,
        type: str | None = None,  # noqa: A002
        year: int | None = None,
        plot: str = 'short',
    ) -> dict:
        """Search with the specified parameters."""
        # build the params
        is_movie: bool | None = None if type is None else (type == 'movie')
        if id is not None:
            res = self.search_by_id(id, is_movie=is_movie, plot=plot)
            return cast(dict, res)

        if title is not None:
            res = self.search_by_title(title, is_movie=is_movie, year=year, plot=plot)
            return cast(dict, res)

        # missing one required argument
        msg = 'At least id or title is required'
        raise ValueError(msg)

    @region.cache_on_arguments(expiration_time=REFINER_EXPIRATION_TIME)
    def search_by_id(
        self,
        imdb_id: int,
        is_movie: bool | None = None,
        plot: str = 'short',
    ) -> dict:
        """Search by IMDB id."""
        # build the params
        params: dict[str, Any] = {'i': imdb_id, 'plot': plot}
        if is_movie is not None:
            type_ = 'movie' if is_movie else 'series'
            params['type'] = type_

        # perform the request
        r = self.session.get(self.base_url, params=params, timeout=self.timeout)
        r.raise_for_status()

        # get the response as json
        j = r.json()

        # check response status
        if j['Response'] == 'False':
            return {}

        return cast(dict, j)

    @region.cache_on_arguments(expiration_time=REFINER_EXPIRATION_TIME)
    def search_by_title(
        self,
        title: str,
        is_movie: bool | None = None,
        year: int | None = None,
        plot: str = 'short',
    ) -> dict:
        """Search by title."""
        # build the params
        params: dict[str, Any] = {'t': title, 'plot': plot}
        if is_movie is not None:
            type_ = 'movie' if is_movie else 'series'
            params['type'] = type_
        if year is not None:
            params['y'] = year

        # perform the request
        r = self.session.get(self.base_url, params=params, timeout=self.timeout)
        r.raise_for_status()

        # get the response as json
        j = r.json()

        # check response status
        if j['Response'] == 'False':
            return {}

        return cast(dict, j)

    @region.cache_on_arguments(expiration_time=REFINER_EXPIRATION_TIME)
    def search(
        self,
        title: str,
        is_movie: bool | None = None,
        year: int | None = None,
        page: int = 1,
    ) -> dict:
        """Search with the specified parameters."""
        # build the params
        params: dict[str, Any] = {'s': title, 'page': page}
        if is_movie is not None:
            type_ = 'movie' if is_movie else 'series'
            params['type'] = type_
        if year is not None:
            params['y'] = year

        # perform the request
        r = self.session.get(self.base_url, params=params, timeout=self.timeout)
        r.raise_for_status()

        # get the response as json
        j = r.json()

        # check response status
        if j['Response'] == 'False':
            return {}

        return cast(dict, j)

    @region.cache_on_arguments(expiration_time=REFINER_EXPIRATION_TIME)
    def search_all(self, title: str, is_movie: bool | None = None, year: int | None = None) -> list:
        """Search with the specified parameters and return all the results."""
        results = self.search(title=title, is_movie=is_movie, year=year)
        if not results:  # pragma: no cover
            return []

        # fetch all paginated results
        all_results = cast(list, results['Search'])
        total_results = int(results['totalResults'])
        page = 1
        while total_results > page * 10:
            page += 1
            results = self.search(title=title, is_movie=is_movie, year=year, page=page)
            if results:  # pragma: no branch
                all_results.extend(cast(list, results['Search']))

        return all_results

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
        # update the default session parameters
        self.session.params['apikey'] = self.apikey  # type: ignore[index]


def refine_episode(client: OMDBClient, video: Episode, *, force: bool = False, **kwargs: Any) -> None:
    """Refine an Episode by searching `OMDb API <https://omdbapi.com/>`_."""
    # exit if the information is complete
    if not force and video.series_imdb_id and video.imdb_id:  # pragma: no cover
        logger.debug('No need to search, IMDB ids already exist for the video.')
        return

    # search the series
    results = client.search_all(video.series, is_movie=False, year=video.year)
    if not results:  # pragma: no cover
        logger.warning('No results for series')
        return
    logger.debug('Found %d results', len(results))

    # filter the results, only if multiple results
    if len(results) > 1:  # pragma: no branch
        results = [r for r in results if video.matches(r['Title'])]
        if not results:  # pragma: no cover
            logger.warning('No matching series found')
            return

    # process the results
    for result in sorted(results, key=operator.itemgetter('Year')):
        if video.original_series and video.year is None:
            logger.debug('Found result for original series without year')
            break

        if video.year == split_year_omdb(result['Year']):
            logger.debug('Found result with matching year')
            break
    else:
        logger.warning('No matching series found')
        return

    # add series information
    logger.debug('Found series %r', result)
    video.series = result['Title']
    video.year = split_year_omdb(result['Year'])
    video.series_imdb_id = decorate_imdb_id(sanitize_id(result['imdbID']))


def refine_movie(client: OMDBClient, video: Movie, *, force: bool = False, **kwargs: Any) -> None:
    """Refine a Movie by searching `OMDb API <https://omdbapi.com/>`_."""
    # exit if the information is complete
    if not force and video.imdb_id:  # pragma: no cover
        logger.debug('No need to search, IMDB ids already exist for the video.')
        return

    # search the movie
    results = client.search_all(video.title, is_movie=True, year=video.year)
    if not results:  # pragma: no cover
        logger.warning('No results for movie')
        return
    logger.debug('Found %d results', len(results))

    # filter the results, only if multiple results
    if len(results) > 1:
        results = [r for r in results if video.matches(r['Title'])]
        if not results:  # pragma: no cover
            logger.warning('No matching movie found')
            return

    # process the results
    for result in results:
        if video.year is None:
            logger.debug('Found result for movie without year')
            break

        if video.year == split_year_omdb(result['Year']):  # pragma: no branch
            logger.debug('Found result with matching year')
            break
    else:  # pragma: no cover
        logger.warning('No matching movie found')
        return

    # add movie information
    logger.debug('Found movie %r', result)
    video.title = result['Title']
    video.year = split_year_omdb(result['Year'])
    video.imdb_id = decorate_imdb_id(sanitize_id(result['imdbID']))


#: Default client
omdb_client = OMDBClient()


def refine(video: Video, *, apikey: str | None = None, force: bool = False, **kwargs: Any) -> Video:
    """Refine a video by searching `OMDb API <https://omdbapi.com/>`_.

    Several :class:`~subliminal.video.Episode` attributes can be found:

      * :attr:`~subliminal.video.Episode.series`
      * :attr:`~subliminal.video.Episode.year`
      * :attr:`~subliminal.video.Episode.series_imdb_id`

    Similarly, for a :class:`~subliminal.video.Movie`:

      * :attr:`~subliminal.video.Movie.title`
      * :attr:`~subliminal.video.Movie.year`
      * :attr:`~subliminal.video.Video.imdb_id`

    :param Video video: the Video to refine.
    :param (str | None) apikey: a personal API key to use OMDb.
    :param bool force: if True, refine even if IMDB id is already known for a Movie or
        if both the IMDB ids of the series and of the episodes are known for an Episode.

    """
    # update the API key
    if apikey is not None:
        omdb_client.apikey = apikey

    # refine for Episode
    if isinstance(video, Episode):
        refine_episode(omdb_client, video, force=force, **kwargs)

    # refine for Movie
    elif isinstance(video, Movie):  # pragma: no branch
        refine_movie(omdb_client, video, force=force, **kwargs)

    return video
