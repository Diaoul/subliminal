# -*- coding: utf-8 -*-
import copy
import io
import logging
import re

from babelfish import Language
from guessit import guessit
try:
    from lxml import etree
except ImportError:  # pragma: no cover
    try:
        import xml.etree.cElementTree as etree
    except ImportError:
        import xml.etree.ElementTree as etree
from requests import Session
from zipfile import ZipFile, is_zipfile

from . import Provider
from .. import __version__
from .. cache import EPISODE_EXPIRATION_TIME, SHOW_EXPIRATION_TIME, region
from .. exceptions import AuthenticationError, ConfigurationError, TooManyRequests
from .. subtitle import (Subtitle, fix_line_ending, guess_matches, sanitize)
from .. video import Episode

logger = logging.getLogger(__name__)


class ItaSASubtitle(Subtitle):
    provider_name = 'itasa'

    def __init__(self, sub_id, series, season, episode, video_format, year, tvdb_id, full_data):
        super(ItaSASubtitle, self).__init__(Language('ita'))
        self.sub_id = sub_id
        self.series = series
        self.season = season
        self.episode = episode
        self.format = video_format
        self.year = year
        self.tvdb_id = tvdb_id
        self.full_data = full_data

    @property
    def id(self):  # pragma: no cover
        return self.sub_id

    def get_matches(self, video, hearing_impaired=False):
        matches = set()

        # series
        if video.series and sanitize(self.series) == sanitize(video.series):
            matches.add('series')
        # season
        if video.season and self.season == video.season:
            matches.add('season')
        # episode
        if video.episode and self.episode == video.episode:
            matches.add('episode')
        # format
        if video.format and video.format.lower() in self.format.lower():
            matches.add('format')
        if video.year and self.year == video.year:
            matches.add('year')
        if video.series_tvdb_id and self.tvdb_id == video.series_tvdb_id:
            matches.add('series_tvdb_id')

        # other properties
        matches |= guess_matches(video, guessit(self.full_data), partial=True)

        return matches


class ItaSAProvider(Provider):
    languages = {Language('ita')}

    video_types = (Episode,)

    server_url = 'https://api.italiansubs.net/api/rest/'

    apikey = 'd86ad6ec041b334fac1e512174ee04d5'

    def __init__(self, username=None, password=None):
        if username is not None and password is None or username is None and password is not None:
            raise ConfigurationError('Username and password must be specified')

        self.username = username
        self.password = password
        self.logged_in = False
        self.login_itasa = False
        self.session = None
        self.auth_code = None

    def initialize(self):
        self.session = Session()
        self.session.headers['User-Agent'] = 'Subliminal/%s' % __version__

        # login
        if self.username is not None and self.password is not None:
            logger.info('Logging in')
            params = {
                'username': self.username,
                'password': self.password,
                'apikey': self.apikey
            }

            r = self.session.get(self.server_url + 'users/login', params=params, allow_redirects=False, timeout=10)
            root = etree.fromstring(r.content)

            if root.find('status').text == 'fail':
                raise AuthenticationError(root.find('error/message').text)

            self.auth_code = root.find('data/user/authcode').text

            r = self.session.get('https://www.italiansubs.net/', allow_redirects=True, timeout=30)
            form = re.search('<form.*?id="form-login".*?>.*?</form>', r.content, re.DOTALL)
            input_matcher = re.finditer('<input.*?name="(.*?)".*?value="(.*?)".*?/>', form.group())

            data = {}

            for inputMatch in input_matcher:
                data[inputMatch.group(1)] = inputMatch.group(2)
            data['username'] = self.username
            data['passwd'] = self.password

            r = self.session.post('https://www.italiansubs.net/index.php', data=data, allow_redirects=True, timeout=30)
            r.raise_for_status()

            self.logged_in = True

    def terminate(self):
        self.session.close()
        self.logged_in = False

    @region.cache_on_arguments(expiration_time=SHOW_EXPIRATION_TIME)
    def _get_show_ids(self):
        """Get the ``dict`` of show ids per series by querying the `shows` page.

        :return: show id per series, lower case and without quotes.
        :rtype: dict

        """
        # get the show page
        logger.info('Getting show ids')
        params = {'apikey': self.apikey}
        r = self.session.get(self.server_url + 'shows', timeout=10, params=params)
        r.raise_for_status()
        root = etree.fromstring(r.content)

        # populate the show ids
        show_ids = {}
        for show in root.findall('data/shows/show'):
            if show.find('name').text is None:  # pragma: no cover
                continue
            show_ids[sanitize(show.find('name').text).lower()] = int(show.find('id').text)
        logger.debug('Found %d show ids', len(show_ids))

        return show_ids

    @region.cache_on_arguments(expiration_time=SHOW_EXPIRATION_TIME)
    def _search_show_id(self, series):
        """Search the show id from the `series`

        :param str series: series of the episode.
        :return: the show id, if found.
        :rtype: int or None

        """
        # build the param
        params = {'apikey': self.apikey, 'q': series}

        # make the search
        logger.info('Searching show ids with %r', params)
        r = self.session.get(self.server_url + 'shows/search', params=params, timeout=10)
        r.raise_for_status()
        root = etree.fromstring(r.content)

        if int(root.find('data/count').text) == 0:
            logger.warning('Show id not found: no suggestion')
            return None

        # Looking for show in first page
        for show in root.findall('data/shows/show'):
            if sanitize(show.find('name').text).lower() == sanitize(series.lower()):
                show_id = int(show.find('id').text)
                logger.debug('Found show id %d', show_id)

                return show_id

        # Not in the first page of result try next (if any)
        next_page = root.find('data/next')
        while next_page.text is not None:  # pragma: no cover

            r = self.session.get(next_page.text, timeout=10)
            r.raise_for_status()
            root = etree.fromstring(r.content)

            logger.info('Loading suggestion page %r', root.find('data/page').text)

            # Looking for show in following pages
            for show in root.findall('data/shows/show'):
                if sanitize(show.find('name').text).lower() == sanitize(series.lower()):
                    show_id = int(show.find('id').text)
                    logger.debug('Found show id %d', show_id)

                    return show_id

            next_page = root.find('data/next')

        # No matches found
        logger.warning('Show id not found: suggestions does not match')

        return None

    def get_show_id(self, series, country_code=None):
        """Get the best matching show id for `series`.

        First search in the result of :meth:`_get_show_ids` and fallback on a search with :meth:`_search_show_id`

        :param str series: series of the episode.
        :param str country_code: the country in which teh show is aired.
        :return: the show id, if found.
        :rtype: int or None

        """
        series_sanitized = sanitize(series).lower()
        show_ids = self._get_show_ids()
        show_id = None

        # attempt with country
        if not show_id and country_code:
            logger.debug('Getting show id with country')
            show_id = show_ids.get('%s %s' % (series_sanitized, country_code.lower()))

        # attempt clean
        if not show_id:
            logger.debug('Getting show id')
            show_id = show_ids.get(series_sanitized)

        # search as last resort
        if not show_id:
            logger.warning('Series not found in show ids')
            show_id = self._search_show_id(series)

        return show_id

    @region.cache_on_arguments(expiration_time=EPISODE_EXPIRATION_TIME)
    def _download_zip(self, sub_id):
        # download the subtitle
        logger.info('Downloading subtitle %r', sub_id)

        params = {
            'authcode': self.auth_code,
            'apikey': self.apikey,
            'subtitle_id': sub_id
        }

        r = self.session.get(self.server_url + 'subtitles/download', params=params, timeout=30)
        r.raise_for_status()

        return r.content

    def _get_season_subtitles(self, show_id, season, sub_format):
        params = {
            'apikey': self.apikey,
            'show_id': show_id,
            'q': 'Stagione %%%d' % season,
            'version': sub_format
        }
        r = self.session.get(self.server_url + 'subtitles/search', params=params, timeout=30)
        r.raise_for_status()
        root = etree.fromstring(r.content)

        if int(root.find('data/count').text) == 0:
            logger.warning('Subtitles for season not found, try with rip suffix')

            params['version'] = sub_format + 'rip'
            r = self.session.get(self.server_url + 'subtitles/search', params=params, timeout=30)
            r.raise_for_status()
            root = etree.fromstring(r.content)
            if int(root.find('data/count').text) == 0:
                logger.warning('Subtitles for season not found')
                return []

        subs = []
        # Looking for subtitles in first page
        season_re = re.compile('.*?stagione 0*?%d.*' % season)
        for subtitle in root.findall('data/subtitles/subtitle'):
            if season_re.match(subtitle.find('name').text.lower()):
                logger.debug('Found season zip id %d - %r - %r',
                             int(subtitle.find('id').text),
                             subtitle.find('name').text,
                             subtitle.find('version').text)

                content = self._download_zip(int(subtitle.find('id').text))
                if not is_zipfile(io.BytesIO(content)):   # pragma: no cover
                    if 'limite di download' in content:
                        raise TooManyRequests()
                    else:
                        raise ConfigurationError('Not a zip file: %r' % content)

                with ZipFile(io.BytesIO(content)) as zf:
                    episode_re = re.compile('s(\d{1,2})e(\d{1,2})')
                    for index, name in enumerate(zf.namelist()):
                        match = episode_re.search(name)
                        if not match:  # pragma: no cover
                            logger.debug('Cannot decode subtitle %r', name)
                        else:
                            sub = ItaSASubtitle(
                                int(subtitle.find('id').text),
                                subtitle.find('show_name').text,
                                int(match.group(1)),
                                int(match.group(2)),
                                None,
                                None,
                                None,
                                name)
                            sub.content = fix_line_ending(zf.read(name))
                            subs.append(sub)

        return subs

    def query(self, series, season, episode, video_format, resolution, country=None):

        # To make queries you need to be logged in
        if not self.logged_in:  # pragma: no cover
            raise ConfigurationError('Cannot query if not logged in')

        # get the show id
        show_id = self.get_show_id(series, country)
        if show_id is None:
            logger.error('No show id found for %r ', series)
            return []

        # get the page of the season of the show
        logger.info('Getting the subtitle of show id %d, season %d episode %d, format %r', show_id,
                    season, episode, video_format)
        subtitles = []

        # Default format is SDTV
        if not video_format or video_format.lower() == 'hdtv':
            if resolution in ('1080i', '1080p', '720p'):
                sub_format = resolution
            else:
                sub_format = 'normale'
        else:
            sub_format = video_format.lower()

        # Look for year
        params = {
            'apikey': self.apikey
        }
        r = self.session.get(self.server_url + 'shows/' + str(show_id), params=params, timeout=30)
        r.raise_for_status()
        root = etree.fromstring(r.content)

        year = root.find('data/show/started').text
        if year:
            year = int(year.split('-', 1)[0])
        tvdb_id = root.find('data/show/id_tvdb').text
        if tvdb_id:
            tvdb_id = int(tvdb_id)

        params = {
            'apikey': self.apikey,
            'show_id': show_id,
            'q': '%dx%02d' % (season, episode),
            'version': sub_format
            }
        r = self.session.get(self.server_url + 'subtitles/search', params=params, timeout=30)
        r.raise_for_status()
        root = etree.fromstring(r.content)

        if int(root.find('data/count').text) == 0:
            logger.warning('Subtitles not found,  try with rip suffix')

            params['version'] = sub_format + 'rip'
            r = self.session.get(self.server_url + 'subtitles/search', params=params, timeout=30)
            r.raise_for_status()
            root = etree.fromstring(r.content)
            if int(root.find('data/count').text) == 0:
                logger.warning('Subtitles not found, go season mode')

                # If no subtitle are found for single episode try to download all season zip
                subs = self._get_season_subtitles(show_id, season, sub_format)
                if subs:
                    for subtitle in subs:
                        subtitle.format = video_format
                        subtitle.year = year
                        subtitle.tvdb_id = tvdb_id

                    return subs
                else:
                    return []

        # Looking for subtitles in first page
        for subtitle in root.findall('data/subtitles/subtitle'):
            if '%dx%02d' % (season, episode) in subtitle.find('name').text.lower():

                logger.debug('Found subtitle id %d - %r - %r',
                             int(subtitle.find('id').text),
                             subtitle.find('name').text,
                             subtitle.find('version').text)

                sub = ItaSASubtitle(
                        int(subtitle.find('id').text),
                        subtitle.find('show_name').text,
                        season,
                        episode,
                        video_format,
                        year,
                        tvdb_id,
                        subtitle.find('name').text)

                subtitles.append(sub)

        # Not in the first page of result try next (if any)
        next_page = root.find('data/next')
        while next_page.text is not None:   # pragma: no cover

            r = self.session.get(next_page.text, timeout=30)
            r.raise_for_status()
            root = etree.fromstring(r.content)

            logger.info('Loading subtitles page %r', root.data.page.text)

            # Looking for show in following pages
            for subtitle in root.findall('data/subtitles/subtitle'):
                if '%dx%02d' % (season, episode) in subtitle.find('name').text.lower():

                    logger.debug('Found subtitle id %d - %r - %r',
                                 int(subtitle.find('id').text),
                                 subtitle.find('name').text,
                                 subtitle.find('version').text)

                    sub = ItaSASubtitle(
                        int(subtitle.find('id').text),
                        subtitle.find('show_name').text,
                        season,
                        episode,
                        video_format,
                        year,
                        tvdb_id,
                        subtitle.find('name').text)

                    subtitles.append(sub)

            next_page = root.find('data/next')

        # Download the subs found, can be more than one in zip
        additional_subs = []
        for sub in subtitles:

            # open the zip
            content = self._download_zip(sub.sub_id)
            if not is_zipfile(io.BytesIO(content)):   # pragma: no cover
                if 'limite di download' in content:
                    raise TooManyRequests()
                else:
                    raise ConfigurationError('Not a zip file: %r' % content)

            with ZipFile(io.BytesIO(content)) as zf:
                if len(zf.namelist()) > 1:   # pragma: no cover

                    for index, name in enumerate(zf.namelist()):

                        if index == 0:
                            # First element
                            sub.content = fix_line_ending(zf.read(name))
                            sub.full_data = name
                        else:
                            add_sub = copy.deepcopy(sub)
                            add_sub.content = fix_line_ending(zf.read(name))
                            add_sub.full_data = name
                            additional_subs.append(add_sub)
                else:
                    sub.content = fix_line_ending(zf.read(zf.namelist()[0]))
                    sub.full_data = zf.namelist()[0]

        return subtitles + additional_subs

    def list_subtitles(self, video, languages):
        return self.query(video.series, video.season, video.episode, video.format, video.resolution)

    def download_subtitle(self, subtitle):   # pragma: no cover
        pass
