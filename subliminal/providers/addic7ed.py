# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
import babelfish
import bs4
import charade
import requests
from . import Provider
from . import IGNORED_CHARACTERS_RE
from .. import __version__
from ..cache import region
from ..exceptions import ProviderConfigurationError, ProviderNotAvailable, InvalidSubtitle
from ..subtitle import Subtitle, is_valid_subtitle
from ..video import Episode


logger = logging.getLogger(__name__)


class Addic7edSubtitle(Subtitle):
    provider_name = 'addic7ed'

    def __init__(self, language, series, season, episode, title, version, hearing_impaired, download_link, referer):
        super(Addic7edSubtitle, self).__init__(language, hearing_impaired)
        self.series = series
        self.season = season
        self.episode = episode
        self.title = title
        self.version = version
        self.download_link = download_link
        self.referer = referer

    def compute_matches(self, video):
        matches = set()
        # series
        if video.series and self.series == video.series:
            matches.add('series')
        # season
        if video.season and self.season == video.season:
            matches.add('season')
        # episode
        if video.episode and self.episode == video.episode:
            matches.add('episode')
        # title
        if video.title and self.title.lower() == video.title.lower():
            matches.add('title')
        # release_group
        if video.release_group and self.version and video.release_group.lower() in self.version.lower():
            matches.add('release_group')
        # resolution
        if video.resolution and self.version and video.resolution in self.version.lower():
            matches.add('resolution')
        return matches


class Addic7edProvider(Provider):
    languages = set([babelfish.Language('por', 'BR')]) | set([babelfish.Language(l)
                 for l in ['ara', 'aze', 'ben', 'bos', 'bul', 'cat', 'ces', 'dan', 'deu', 'ell', 'eng', 'eus', 'fas',
                           'fin', 'fra', 'glg', 'heb', 'hrv', 'hun', 'hye', 'ind', 'ita', 'jpn', 'kor', 'mkd', 'msa',
                           'nld', 'nor', 'pol', 'por', 'ron', 'rus', 'slk', 'slv', 'spa', 'sqi', 'srp', 'swe', 'tha',
                           'tur', 'ukr', 'vie', 'zho']])
    video_types = (Episode,)
    server = 'http://www.addic7ed.com'

    def initialize(self):
        self.session = requests.Session()
        self.session.headers = {
            'User-Agent': self.random_user_agent,
            'Referer': self.server,
        }

    def get(self, url, params=None):
        """Make a GET request on `url` with the given parameters

        :param string url: part of the URL to reach with the leading slash
        :param params: params of the request
        :return: the response
        :rtype: :class:`bs4.BeautifulSoup`
        :raise: :class:`~subliminal.exceptions.ProviderNotAvailable`

        """
        try:
            r = self.session.get(self.server + url, params=params, timeout=30)
        except requests.Timeout:
            raise ProviderNotAvailable('Timeout after 10 seconds')
        if r.status_code != 200:
            raise ProviderNotAvailable('Request failed with status code %d' % r.status_code)
        return bs4.BeautifulSoup(r.content, ['permissive'])

    @region.cache_on_arguments()
    def get_show_ids(self):
        """Load the shows page with default series to show ids mapping

        :return: series to show ids
        :rtype: dict

        """
        soup = self.get('/shows.php')
        show_ids = {}
        for html_show in soup.select('td.version > h3 > a[href^="/show/"]'):
            show_ids[
                IGNORED_CHARACTERS_RE.sub('', html_show.string).lower()] = \
                    int(html_show['href'][6:])
        return show_ids

    @region.cache_on_arguments()
    def find_show_id(self, series):
        """Find a show id from the series

        Use this only if the series is not in the dict returned by :meth:`get_show_ids`

        :param string series: series of the episode
        :return: the show id, if any
        :rtype: int or None

        """
        params = {'search': series, 'Submit': 'Search'}
        logger.debug('Searching series %r', params)
        suggested_shows = self.get('/search.php', params).select('span.titulo > a[href^="/show/"]')
        if not suggested_shows:
            logger.info('Series %r not found', series)
            return None
        return int(suggested_shows[0]['href'][6:])

    def query(self, series, season):
        show_ids = self.get_show_ids()
        _series = IGNORED_CHARACTERS_RE.sub('', series).lower()
        if _series in show_ids:
            show_id = show_ids[_series]
        else:
            show_id = self.find_show_id(_series)
            if show_id is None:
                return []
        params = {'show_id': show_id, 'season': season}
        logger.debug('Searching subtitles %r', params)
        link = '/show/{show_id}&season={season}'.format(**params)
        soup = self.get(link)
        subtitles = []
        for row in soup('tr', class_='epeven completed'):
            cells = row('td')
            if cells[5].string != 'Completed':
                logger.debug('Skipping incomplete subtitle')
                continue
            if not cells[3].string:
                logger.debug('Skipping empty language')
                continue
            subtitles.append(Addic7edSubtitle(babelfish.Language.fromaddic7ed(cells[3].string), series, season,
                                              int(cells[1].string), cells[2].string, cells[4].string,
                                              bool(cells[6].string), cells[9].a['href'], link))
        return subtitles

    def list_subtitles(self, video, languages):
        return [s for s in self.query(video.series, video.season)
                if s.language in languages and s.episode == video.episode]

    def download_subtitle(self, subtitle):
        try:
            r = self.session.get(self.server + subtitle.download_link, timeout=30,
                                 headers={'Referer': self.server + subtitle.referer})
        except requests.Timeout:
            raise ProviderNotAvailable('Timeout after 10 seconds')
        if r.status_code != 200:
            raise ProviderNotAvailable('Request failed with status code %d' % r.status_code)
        if r.headers['Content-Type'] == 'text/html':
            raise ProviderNotAvailable('Download limit exceeded')
        subtitle_text = r.content.decode(charade.detect(r.content)['encoding'], 'replace')
        if not is_valid_subtitle(subtitle_text):
            raise InvalidSubtitle
        return subtitle_text
