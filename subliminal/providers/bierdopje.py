# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
import urllib
import babelfish
import bs4
import charade
import guessit
import requests
from . import Provider
from .. import __version__
from ..cache import region
from ..exceptions import InvalidSubtitle, ProviderNotAvailable, ProviderError
from ..subtitle import Subtitle, is_valid_subtitle, compute_guess_matches
from ..video import Episode


logger = logging.getLogger(__name__)


class BierDopjeSubtitle(Subtitle):
    provider_name = 'bierdopje'

    def __init__(self, language, season, episode, tvdb_id, series, filename, download_link):
        super(BierDopjeSubtitle, self).__init__(language)
        self.season = season
        self.episode = episode
        self.tvdb_id = tvdb_id
        self.series = series
        self.filename = filename
        self.download_link = download_link

    def compute_matches(self, video):
        matches = set()
        # tvdb_id
        if video.tvdb_id and self.tvdb_id == video.tvdb_id:
            matches.add('tvdb_id')
        # series
        if video.series and self.series == video.series:
            matches.add('series')
        # season
        if video.season and self.season == video.season:
            matches.add('season')
        # episode
        if video.episode and self.episode == video.episode:
            matches.add('episode')
        matches |= compute_guess_matches(video, guessit.guess_episode_info(self.filename + '.mkv'))
        return matches


class BierDopjeProvider(Provider):
    languages = {babelfish.Language(l) for l in ['eng', 'nld']}
    video_types = (Episode,)

    def initialize(self):
        self.session = requests.Session()
        self.session.headers = {'User-Agent': 'Subliminal/%s' % __version__}

    def terminate(self):
        self.session.close()

    def get(self, url, **params):
        """Make a GET request on the `url` formatted with `**params`

        :param string url: API part of the URL to reach without the leading slash
        :param \*\*params: format specs for the `url`
        :return: the response
        :rtype: :class:`bs4.BeautifulSoup`
        :raise: :class:`~subliminal.exceptions.ProviderNotAvailable`

        """
        try:
            r = self.session.get('http://api.bierdopje.com/A2B638AC5D804C2E/' + url.format(**params), timeout=10)
        except requests.Timeout:
            raise ProviderNotAvailable('Timeout after 10 seconds')
        if r.status_code == 429:
            raise ProviderNotAvailable('Too Many Requests')
        elif r.status_code != 200:
            raise ProviderError('Request failed with status code %d' % r.status_code)
        return bs4.BeautifulSoup(r.content, ['xml'])

    @region.cache_on_arguments()
    def find_show_id(self, series):
        """Find the show id from series name

        :param string series: series of the episode
        :return: show id
        :rtype: int

        """
        logger.debug('Searching for series %r', series)
        soup = self.get('FindShowByName/{series}', series=urllib.quote(series))
        if soup.status.contents[0] == 'false':
            logger.info('Series %r not found', series)
            return None
        return int(soup.showid.contents[0])

    def query(self, language, season, episode, tvdb_id=None, series=None):
        params = {'language': language.alpha2, 'season': season, 'episode': episode}
        if tvdb_id is not None:
            params['showid'] = tvdb_id
            params['istvdbid'] = 'true'
        elif series is not None:
            show_id = self.find_show_id(series)
            if show_id is None:
                return []
            params['showid'] = show_id
            params['istvdbid'] = 'false'
        else:
            raise ValueError('Missing parameter tvdb_id or series')
        logger.debug('Searching subtitles %r', params)
        soup = self.get('GetAllSubsFor/{showid}/{season}/{episode}/{language}/{istvdbid}', **params)
        if soup.status.contents[0] == 'false':
            logger.debug('No subtitle found')
            return []
        logger.debug('Found subtitles %r', soup.results('result'))
        return [BierDopjeSubtitle(language, season, episode, tvdb_id, series, result.filename.contents[0],
                                  result.downloadlink.contents[0]) for result in soup.results('result')]

    def list_subtitles(self, video, languages):
        subtitles = []
        for language in languages:
            subtitles.extend(self.query(language, video.season, video.episode, video.tvdb_id, video.series))
        return subtitles

    def download_subtitle(self, subtitle):
        try:
            r = self.session.get(subtitle.download_link, timeout=10)
        except requests.Timeout:
            raise ProviderNotAvailable('Timeout after 10 seconds')
        if r.status_code == 429:
            raise ProviderNotAvailable('Too Many Requests')
        elif r.status_code != 200:
            raise ProviderError('Request failed with status code %d' % r.status_code)
        subtitle_text = r.content.decode(charade.detect(r.content)['encoding'])
        if not is_valid_subtitle(subtitle_text):
            raise InvalidSubtitle
        return subtitle_text
