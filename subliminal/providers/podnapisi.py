# -*- coding: utf-8 -*-
import io
import logging
import re

from babelfish import Language, language_converters
from guessit import guess_episode_info, guess_movie_info
try:
    from lxml import etree
except ImportError:
    try:
        import xml.etree.cElementTree as etree
    except ImportError:
        import xml.etree.ElementTree as etree
from requests import Session
from zipfile import ZipFile

from . import Provider, get_version
from .. import __version__
from ..exceptions import ProviderError
from ..subtitle import Subtitle, fix_line_ending, guess_matches, sanitized_string_equal
from ..video import Episode, Movie

logger = logging.getLogger(__name__)


class PodnapisiSubtitle(Subtitle):
    provider_name = 'podnapisi'

    def __init__(self, language, hearing_impaired, page_link, pid, releases, title, season=None, episode=None,
                 year=None):
        super(PodnapisiSubtitle, self).__init__(language, hearing_impaired, page_link)
        self.pid = pid
        self.releases = releases
        self.title = title
        self.season = season
        self.episode = episode
        self.year = year

    @property
    def id(self):
        return self.pid

    def get_matches(self, video, hearing_impaired=False):
        matches = super(PodnapisiSubtitle, self).get_matches(video, hearing_impaired=hearing_impaired)

        # episode
        if isinstance(video, Episode):
            # series
            if video.series and sanitized_string_equal(self.title, video.series):
                matches.add('series')
            # season
            if video.season and self.season == video.season:
                matches.add('season')
            # episode
            if video.episode and self.episode == video.episode:
                matches.add('episode')
            # guess
            for release in self.releases:
                matches |= guess_matches(video, guess_episode_info(release + '.mkv'))
        # movie
        elif isinstance(video, Movie):
            # title
            if video.title and sanitized_string_equal(self.title, video.title):
                matches.add('title')
            # guess
            for release in self.releases:
                matches |= guess_matches(video, guess_movie_info(release + '.mkv'))
        # year
        if video.year and self.year == video.year:
            matches.add('year')

        return matches


class PodnapisiProvider(Provider):
    languages = ({Language('por', 'BR'), Language('srp', script='Latn')} |
                 {Language.fromalpha2(l) for l in language_converters['alpha2'].codes})
    video_types = (Episode, Movie)
    server_url = 'http://podnapisi.net/subtitles/'

    def initialize(self):
        self.session = Session()
        self.session.headers = {'User-Agent': 'Subliminal/%s' % get_version(__version__)}

    def terminate(self):
        self.session.close()

    def query(self, language, keyword, season=None, episode=None, year=None):
        # set parameters, see http://www.podnapisi.net/forum/viewtopic.php?f=62&t=26164#p212652
        params = {'sXML': 1, 'sL': str(language), 'sK': keyword}
        is_episode = False
        if season and episode:
            is_episode = True
            params['sTS'] = season
            params['sTE'] = episode
        if year:
            params['sY'] = year

        # loop over paginated results
        logger.info('Searching subtitles %r', params)
        subtitles = []
        pids = set()
        while True:
            # query the server
            xml = etree.fromstring(self.session.get(self.server_url + 'search/old', params=params, timeout=10).content)

            # exit if no results
            if not int(xml.find('pagination/results').text):
                logger.debug('No subtitles found')
                break

            # loop over subtitles
            for subtitle_xml in xml.findall('subtitle'):
                # read xml elements
                language = Language.fromietf(subtitle_xml.find('language').text)
                hearing_impaired = 'n' in (subtitle_xml.find('flags').text or '')
                page_link = subtitle_xml.find('url').text
                pid = subtitle_xml.find('pid').text
                releases = []
                if subtitle_xml.find('release').text:
                    for release in subtitle_xml.find('release').text.split():
                        release = re.sub(r'\.+$', '', release)  # remove trailing dots
                        release = ''.join(filter(lambda x: ord(x) < 128, release))  # remove non-ascii characters
                        releases.append(release)
                title = subtitle_xml.find('title').text
                season = int(subtitle_xml.find('tvSeason').text)
                episode = int(subtitle_xml.find('tvEpisode').text)
                year = int(subtitle_xml.find('year').text)

                if is_episode:
                    subtitle = PodnapisiSubtitle(language, hearing_impaired, page_link, pid, releases, title,
                                                 season=season, episode=episode, year=year)
                else:
                    subtitle = PodnapisiSubtitle(language, hearing_impaired, page_link, pid, releases, title,
                                                 year=year)

                # ignore duplicates, see http://www.podnapisi.net/forum/viewtopic.php?f=62&t=26164&start=10#p213321
                if pid in pids:
                    continue

                logger.debug('Found subtitle %r', subtitle)
                subtitles.append(subtitle)
                pids.add(pid)

            # stop on last page
            if int(xml.find('pagination/current').text) >= int(xml.find('pagination/count').text):
                break

            # increment current page
            params['page'] = int(xml.find('pagination/current').text) + 1
            logger.debug('Getting page %d', params['page'])

        return subtitles

    def list_subtitles(self, video, languages):
        if isinstance(video, Episode):
            return [s for l in languages for s in self.query(l, video.series, season=video.season,
                                                             episode=video.episode, year=video.year)]
        elif isinstance(video, Movie):
            return [s for l in languages for s in self.query(l, video.title, year=video.year)]

    def download_subtitle(self, subtitle):
        # download as a zip
        logger.info('Downloading subtitle %r', subtitle)
        r = self.session.get(self.server_url + subtitle.pid + '/download', params={'container': 'zip'}, timeout=10)
        r.raise_for_status()

        # open the zip
        with ZipFile(io.BytesIO(r.content)) as zf:
            if len(zf.namelist()) > 1:
                raise ProviderError('More than one file to unzip')

            subtitle.content = fix_line_ending(zf.read(zf.namelist()[0]))
