# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from functools import wraps
import logging

import requests

from .. import __short_version__
from ..cache import REFINER_EXPIRATION_TIME, region
from ..video import Episode

logger = logging.getLogger(__name__)


def requires_auth(func):
    """Decorator for :class:`TVDBClient` methods that require authentication"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.token is None or self.token_expired:
            self.login()
        elif self.token_needs_refresh:
            self.refresh_token()
        return func(self, *args, **kwargs)
    return wrapper


class TVDBClient(object):
    """TVDB REST API Client

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
    base_url = 'https://api-beta.thetvdb.com'

    #: Token lifespan
    token_lifespan = timedelta(hours=1)

    #: Minimum token age before a :meth:`refresh_token` is triggered
    refresh_token_every = timedelta(minutes=30)

    def __init__(self, apikey=None, username=None, password=None, language='en', session=None, headers=None,
                 timeout=10):
        #: API key
        self.apikey = apikey

        #: Username
        self.username = username

        #: Password
        self.password = password

        #: Last token acquisition date
        self.token_date = datetime.utcnow() - self.token_lifespan

        #: Session for the requests
        self.session = session or requests.Session()
        self.session.timeout = timeout
        self.session.headers.update(headers or {})
        self.session.headers['Content-Type'] = 'application/json'
        self.session.headers['Accept-Language'] = language

    @property
    def language(self):
        return self.session.headers['Accept-Language']

    @language.setter
    def language(self, value):
        self.session.headers['Accept-Language'] = value

    @property
    def token(self):
        if 'Authorization' not in self.session.headers:
            return None
        return self.session.headers['Authorization'][7:]

    @property
    def token_expired(self):
        return datetime.utcnow() - self.token_date > self.token_lifespan

    @property
    def token_needs_refresh(self):
        return datetime.utcnow() - self.token_date > self.refresh_token_every

    def login(self):
        """Login"""
        # perform the request
        data = {'apikey': self.apikey, 'username': self.username, 'password': self.password}
        r = self.session.post(self.base_url + '/login', json=data)
        r.raise_for_status()

        # set the Authorization header
        self.session.headers['Authorization'] = 'Bearer ' + r.json()['token']

        # update token_date
        self.token_date = datetime.utcnow()

    def refresh_token(self):
        """Refresh token"""
        # perform the request
        r = self.session.get(self.base_url + '/refresh_token')
        r.raise_for_status()

        # set the Authorization header
        self.session.headers['Authorization'] = 'Bearer ' + r.json()['token']

        # update token_date
        self.token_date = datetime.utcnow()

    @requires_auth
    def search_series(self, name=None, imdb_id=None, zap2it_id=None):
        """Search series"""
        # perform the request
        params = {'name': name, 'imdbId': imdb_id, 'zap2itId': zap2it_id}
        r = self.session.get(self.base_url + '/search/series', params=params)
        if r.status_code == 404:
            return None
        r.raise_for_status()

        return r.json()['data']

    @requires_auth
    def get_series(self, id):
        """Get series"""
        # perform the request
        r = self.session.get(self.base_url + '/series/{}'.format(id))
        if r.status_code == 404:
            return None
        r.raise_for_status()

        return r.json()['data']

    @requires_auth
    def get_series_actors(self, id):
        """Get series actors"""
        # perform the request
        r = self.session.get(self.base_url + '/series/{}/actors'.format(id))
        if r.status_code == 404:
            return None
        r.raise_for_status()

        return r.json()['data']

    @requires_auth
    def get_series_episodes(self, id, page=1):
        """Get series episodes"""
        # perform the request
        params = {'page': page}
        r = self.session.get(self.base_url + '/series/{}/episodes'.format(id), params=params)
        if r.status_code == 404:
            return None
        r.raise_for_status()

        return r.json()

    @requires_auth
    def query_series_episodes(self, id, absolute_number=None, aired_season=None, aired_episode=None, dvd_season=None,
                              dvd_episode=None, imdb_id=None, page=1):
        """Query series episodes"""
        # perform the request
        params = {'absoluteNumber': absolute_number, 'airedSeason': aired_season, 'airedEpisode': aired_episode,
                  'dvdSeason': dvd_season, 'dvdEpisode': dvd_episode, 'imdbId': imdb_id, 'page': page}
        r = self.session.get(self.base_url + '/series/{}/episodes/query'.format(id), params=params)
        if r.status_code == 404:
            return None
        r.raise_for_status()

        return r.json()

    @requires_auth
    def get_episode(self, id):
        """Get episode"""
        # perform the request
        r = self.session.get(self.base_url + '/episodes/{}'.format(id))
        if r.status_code == 404:
            return None
        r.raise_for_status()

        return r.json()['data']


#: Configured instance of :class:`TVDBClient`
tvdb_client = TVDBClient('5EC930FB90DA1ADA', headers={'User-Agent': 'Subliminal/%s' % __short_version__})


@region.cache_on_arguments(expiration_time=REFINER_EXPIRATION_TIME)
def search_series(name):
    """Search series and sort the results by likelihood.

     Prefer series with the same name and with continuing status.

    :param str name: name of the series.
    :return: the search results.
    :rtype: list

    """
    results = tvdb_client.search_series(name)
    if not results:
        return None

    def match(series):
        key = 0
        if series['status'] != 'Continuing':
            key += 1
        if series['seriesName'] != name:
            key += 2

        return key

    return sorted(results, key=match)


@region.cache_on_arguments(expiration_time=REFINER_EXPIRATION_TIME)
def get_series(id):
    """Get series.

    :param int id: id of the series.
    :return: the series data.
    :rtype: dict

    """
    return tvdb_client.get_series(id)


@region.cache_on_arguments(expiration_time=REFINER_EXPIRATION_TIME)
def get_series_episode(series_id, season, episode):
    """Get an episode of a series.

    :param int series_id: id of the series.
    :param int season: season number of the episode.
    :param int episode: episode number of the episode.
    :return: the episode data.
    :rtype: dict

    """
    result = tvdb_client.query_series_episodes(series_id, aired_season=season, aired_episode=episode)
    if result:
        return tvdb_client.get_episode(result['data'][0]['id'])


def refine(video, **kwargs):
    """Refine a video by searching `TheTVDB <http://thetvdb.com/>`_.

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

    """
    # only deal with Episode videos
    if not isinstance(video, Episode):
        logger.error('Cannot refine episodes')
        return

    # exit if the information is complete
    if video.series_tvdb_id and video.tvdb_id:
        logger.debug('No need to search')
        return

    # search the series
    logger.info('Searching series %r', video.series)
    results = search_series(video.series.lower())
    if not results:
        logger.warning('No results for series')
        return
    logger.debug('Found %d results', len(results))

    # process the results
    found = False
    for result in results:
        if video.original_series and video.year is None:
            logger.debug('Found result for original series without year')
            found = True
            break
        if video.year == datetime.strptime(result['firstAired'], '%Y-%m-%d').year:
            logger.debug('Found result with matching year')
            found = True
            break

    if not found:
        logger.warning('No matching series found')
        return

    # get the series
    result = get_series(result['id'])

    # add series information
    logger.debug('Found series %r', result)
    video.series = result['seriesName']
    video.year = datetime.strptime(result['firstAired'], '%Y-%m-%d').year
    video.series_imdb_id = result['imdbId']
    video.series_tvdb_id = result['id']

    # get the episode
    logger.info('Getting series episode %dx%d', video.season, video.episode)
    result = get_series_episode(video.series_tvdb_id, video.season, video.episode)
    if not result:
        logger.warning('No results for episode')
        return

    # add episode information
    logger.debug('Found episode %r', result)
    video.title = result['episodeName']
    video.imdb_id = result['imdbId']
    video.tvdb_id = result['id']
