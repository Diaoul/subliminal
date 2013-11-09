# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
import urllib
import babelfish
import charade
import guessit
import requests
import xml.etree.ElementTree
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
        :rtype: :class:`xml.etree.ElementTree.Element`
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
        return xml.etree.ElementTree.fromstring(r.content)

    @region.cache_on_arguments()
    def find_show_id(self, series):
        """Find the show id from series name

        :param string series: series of the episode
        :return: show id
        :rtype: int

        """
        logger.debug('Searching for series %r', series)
        root = self.get('FindShowByName/{series}', series=urllib.quote(series))
        if root.find('response/status').text == 'false':
            logger.info('Series %r not found', series)
            return None
        return int(root.find('response/results/result[1]/showid').text)

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
        root = self.get('GetAllSubsFor/{showid}/{season}/{episode}/{language}/{istvdbid}', **params)
        if root.find('response/status').text == 'false':
            logger.debug('No subtitle found')
            return []
        logger.debug('Found subtitles %r', root.find('response/results'))
        return [BierDopjeSubtitle(language, season, episode, tvdb_id, series, result.find('filename').text,
                                  result.find('downloadlink').text) for result in root.find('response/results')]

    def list_subtitles(self, video, languages):
        return [s for l in languages for s in self.query(l, video.season, video.episode, video.tvdb_id, video.series)]

    def download_subtitle(self, subtitle):
        try:
            r = self.session.get(subtitle.download_link, timeout=10)
        except requests.Timeout:
            raise ProviderNotAvailable('Timeout after 10 seconds')
        if r.status_code == 429:
            raise ProviderNotAvailable('Too Many Requests')
        elif r.status_code != 200:
            raise ProviderError('Request failed with status code %d' % r.status_code)
        subtitle_text = r.content.decode(charade.detect(r.content)['encoding'], 'replace')
        if not is_valid_subtitle(subtitle_text):
            raise InvalidSubtitle
        return subtitle_text
