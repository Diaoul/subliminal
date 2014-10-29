# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
import re
import io
import zipfile

import babelfish
import bs4
import charade
import requests

from . import Provider
from .. import __version__
from ..cache import region
from ..exceptions import ProviderNotAvailable, InvalidSubtitle, ProviderError, Error
from ..subtitle import Subtitle, is_valid_subtitle
from ..video import Episode


__author__ = 'ningod'

logger = logging.getLogger(__name__)


class ItasaSubtitle(Subtitle):
    provider_name = 'itasa'

    def __str__(self):
        return self.series + '.S' + str(self.season) + 'E' + str(self.episode) + ' [' + self.download_link + '] '

    def __init__(self, series, season, episode, download_link, page_link):
        super(ItasaSubtitle, self).__init__(babelfish.Language('ita'), False)
        self.series = series
        self.season = season
        self.episode = episode
        self.download_link = download_link
        self.page_link = page_link

    def compute_matches(self, video):
        matches = set()
        logger.debug('compute_matches')
        # episode
        if isinstance(video, Episode):
            # series
            if video.series and self.series.lower() == video.series.lower():
                logger.debug('matches series')
                matches.add('series')
            # season
            if video.season and self.season == video.season:
                logger.debug('matches season')
                matches.add('season')
            # episode
            if video.episode and self.episode == video.episode:
                logger.debug('matches episode')
                matches.add('episode')

        return matches


class ItasaProvider(Provider):
    languages = {babelfish.Language(l) for l in ['ita']}
    video_types = (Episode,)
    server = 'http://www.italiansubs.net'

    def __init__(self, username=None, password=None):
        super(ItasaProvider, self).__init__()
        self.username = username
        self.password = password
        self.logged_in = False

    def initialize(self):
        if self.username is None or self.password is None:
            raise ProviderNotAvailable('Username and password must be specified')
        self.session = requests.Session()
        self.session.headers = {'User-Agent': 'Subliminal/%s' % __version__.split('-')[0]}
        # login
        if self.username is not None and self.password is not None:
            logger.debug('Logging in')
            r = self.session.get(self.server + '/index.php?option=com_remository')
            if r.status_code != 200:
                raise ProviderError('Request failed with status code %d' % r.status_code)
            matchlogin = re.search('name=.return.*?value="(.*?)".*?name="(.*?)" value="1"', r.text, re.DOTALL)
            self.returnval = matchlogin.group(1)
            self.sessionval = matchlogin.group(2)
            logger.debug('returnval: ' + self.returnval + ' sessionval: ' + self.sessionval)
            login_data = {'username': self.username,
                          'passwd': self.password,
                          'remember': 'yes',
                          'Submit': 'Login',
                          'option': 'com_user',
                          'task': 'login',
                          'silent': 'true',
                          'return': self.returnval,
                          self.sessionval: '1'}
            r = self.session.post(self.server + '/index.php', login_data, timeout=10, allow_redirects=True)
            login_cookies = self.session.cookies.keys()
            if 'PHPSESSID' in login_cookies:
                token = True
            else:
                token = None
            if r.status_code == 200 and token is not None:
                logger.info('Logged in')
                self.logged_in = True
            else:
                raise Error('user: ' + self.username + ' not authenticated')

    def terminate(self):
        # logout
        if self.logged_in:
            logout_data = {'option': 'com_user', 'task': 'logout', 'silent': 'true', 'return': self.returnval}
            r = self.session.post(self.server + '/index.php', logout_data, timeout=10, allow_redirects=False)
            logger.info('Logged out')
            if r.status_code != 301:
                raise ProviderError('Request failed with status code' + r.status_code)
        self.session.close()

    def get(self, url, params=None):
        """Make a GET request on `url` with the given parameters

        :param string url: part of the URL to reach with the leading slash
        :param params: params of the request
        :return: the response
        :rtype: :class:`bs4.BeautifulSoup`

        """
        r = self.session.get(url, params=params, timeout=10)
        if r.status_code != 200:
            raise ProviderError('Request failed with status code %d' % r.status_code)
        return bs4.BeautifulSoup(r.content, ['permissive'])

    @region.cache_on_arguments()
    def get_shows(self):
        """Load the shows page with default series to show ids mapping

        :return: series to show ids
        :rtype: dict

        """
        soup = self.get(self.server + '/index.php?option=com_remository')
        show_ids = {}
        for html_show in soup.select('div#remositorycontainerlist > table > tbody > tr[id^=""]'):
            show_ids[html_show['id'].lower()] = html_show.select('td > h3 > a[href^=""]')[1]['href']
        return show_ids

    def query(self, series, season, episode, resolution='480p', year=None):
        subtitles = []

        shows = self.get_shows()
        show_link = None
        if year is not None:  # search with the year
            series_year = '%s (%d)' % (series.lower(), year)
            if series_year in shows:
                show = shows[series_year]
        if show_link is None:  # search without the year
            year = None
            if series.lower() in shows:
                show_link = shows[series.lower()]
        if show_link is None:
            return subtitles
        logger.debug('show_link: ' + show_link)
        show_soup = self.get(show_link)
        seasons = {}
        season_link = None
        resolution_link = None
        episode_link = None
        for html_season in show_soup.select('div#remositorycontainerlist > table > tbody > tr[id^=""]'):
            seasons[int(html_season['id'][9:])] = html_season.select('td > h3 > a[href^=""]')[1]['href']
        if int(season) in seasons:
            season_link = seasons[int(season)]
        if season_link is None:
            return subtitles
        logger.debug('season_link: ' + season_link)
        season_soup = self.get(season_link)
        if resolution is not None and resolution != '480p':
            logger.debug('Search for resolution: ' + resolution)
            resolutions = {}
            for html_resolution in season_soup.select('div#remositorycontainerlist > table > tbody > tr[id^=""]'):
                resolutions[html_resolution['id']] = html_resolution.select('td > h3 > a[href^=""]')[1]['href']
            if resolution in resolutions:
                resolution_link = resolutions[resolution]
            if resolution_link is None:
                return subtitles
            logger.debug('resolution_link: ' + resolution_link)
            season_soup = self.get(resolution_link)
        if season_soup == None:
            return subtitles
        episodes = {}
        for html_episode in season_soup.select('div#remositoryfilelisting > div.remolist > dl > dd '):
            series_id = html_episode.select('a')[1].string
            if ( series_id == None ):
                raise Error('parsing error')
            episode_match = re.search(' ([0-9]+x([0-9]+))(?: )?$', series_id)
            if ( episode_match == None ):
                continue
            episode_id = episode_match.group(2)
            if ( episode_id == None ):
                raise Error('parsing error')
            episodes[int(episode_id)] = html_episode.select('a')[1]['href']
        if episode in episodes:
            episode_link = episodes[episode]
        if episode_link is None:
            return subtitles
        logger.debug('episode_link: ' + episode_link)
        download_soup = self.get(episode_link)
        download_link = download_soup.select('div#remositoryfileinfo > dt > center > a[href^=""]')[0]['href']
        logger.debug('download_link: ' + download_link)
        if download_link is None:
            return subtitles
        tmp = ItasaSubtitle(series, season, episode, download_link, episode_link)
        logger.debug('subtitle found ' + str(tmp))
        subtitles = [tmp]
        return subtitles

    def list_subtitles(self, video, languages):
        logger.debug('video: ' + str(video))
        logger.debug('languages: ' + str(languages))
        if babelfish.Language('ita') not in languages:
            return []
        query_result = self.query(video.series, video.season, video.episode, video.resolution, None)
        return query_result

    def download_subtitle(self, subtitle):
        try:
            r = self.session.get(subtitle.download_link, timeout=10, headers={'Referer': subtitle.page_link})
        except requests.Timeout:
            raise ProviderNotAvailable('Timeout after 10 seconds')
        if r.status_code != 200:
            raise ProviderNotAvailable('Download Request failed with status code %d' % r.status_code)
        try:
            with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
                if len(zf.namelist()) > 1:
                    raise Error('More than one file to unzip')
                subtitle_bytes = zf.read(zf.namelist()[0])
        except Exception as e:
            raise ProviderError('Error during unzip')
        subtitle_text = subtitle_bytes.decode(charade.detect(subtitle_bytes)['encoding'], 'replace')
        if not is_valid_subtitle(subtitle_text):
            raise InvalidSubtitle
        return subtitle_text
