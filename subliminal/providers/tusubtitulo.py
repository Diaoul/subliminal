# -*- coding: utf-8 -*-
import logging
import re

from babelfish import Language, language_converters
from guessit import guessit
from requests import Session

from . import ParserBeautifulSoup, Provider
from .. import __short_version__
from ..cache import SHOW_EXPIRATION_TIME, region
from ..exceptions import ProviderError  # , DownloadLimitExceeded, TooManyRequests
from ..score import get_equivalent_release_groups
from ..subtitle import Subtitle, fix_line_ending, guess_matches
from ..utils import sanitize, sanitize_release_group
from ..video import Episode

logger = logging.getLogger(__name__)

language_converters.register('tusubtitulo = subliminal.converters.tusubtitulo:TuSubtituloConverter')

#: Release parsing regex
release_pattern = re.compile('Versi.+n (.+)')


class TuSubtituloSubtitle(Subtitle):
    """TuSubtitulo Subtitle."""
    provider_name = 'tusubtitulo'

    def __init__(self, language, hearing_impaired, page_link, series, season, episode, title, year, version,
                 download_link):
        super(TuSubtituloSubtitle, self).__init__(language, hearing_impaired, page_link)
        self.page_link = page_link
        self.series = series
        self.season = season
        self.episode = episode
        self.title = title
        self.year = year
        self.version = version
        self.download_link = download_link

    @property
    def id(self):
        return self.download_link

    def get_matches(self, video):
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
        # title
        if video.title and sanitize(self.title) == sanitize(video.title):
            matches.add('title')
        # year
        if video.original_series and self.year is None or video.year and video.year == self.year:
            matches.add('year')
        # release_group
        if (video.release_group and self.version and
                any(r in sanitize_release_group(self.version)
                    for r in get_equivalent_release_groups(sanitize_release_group(video.release_group)))):
            matches.add('release_group')
        # resolution
        if video.resolution and self.version and video.resolution in self.version.lower():
            matches.add('resolution')
        # format
        if video.format and self.version and video.format.lower() in self.version.lower():
            matches.add('format')
        # other properties
        matches |= guess_matches(video, guessit(self.version), partial=True)

        return matches


class TuSubtituloProvider(Provider):
    """TuSubtitulo Provider."""
    languages = {Language('por', 'BR')} | {Language(l) for l in [
        'cat', 'eng', 'glg', 'por', 'spa'
    ]}
    video_types = (Episode,)
    server_url = 'https://www.tusubtitulo.com/'
    series_url = server_url + 'series.php'
    subtitles_url = server_url + 'ajax_loadShow.php'

    def __init__(self):
        self.session = None

    def initialize(self):
        self.session = Session()
        self.session.headers['User-Agent'] = 'Subliminal/%s' % __short_version__
        # self.session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:56.0) Gecko/20100101 ' \
        #                                      'Firefox/56.0 '

    def terminate(self):
        self.session.close()

    @region.cache_on_arguments(expiration_time=SHOW_EXPIRATION_TIME)
    def _get_show_ids(self):
        """Get the ``dict`` of show ids per series by querying the `series.php` page.

        :return: show id per series, lower case and without quotes.
        :rtype: dict

        """
        # get the show page
        logger.info('Getting show ids')
        r = self.session.get(self.series_url, timeout=10)
        r.raise_for_status()

        if r.status_code != 200:
            logger.error('Error getting show ids')
            raise ProviderError('Error getting show ids')

        soup = ParserBeautifulSoup(r.content, ['lxml', 'html.parser'])

        # populate the show ids
        show_ids = {}
        for show in soup.select('td > a[href^="/show/"]'):
            show_ids[sanitize(show.get_text())] = int(show['href'][6:])
        logger.debug('Found %d show ids', len(show_ids))

        return show_ids

    def get_show_id(self, series, year=None):
        """Get the best matching show id for `series` and `year`.

        :param str series: series of the episode.
        :param year: year of the series, if any.
        :type year: int
        :return: the show id, if found.
        :rtype: int

        """
        series_sanitized = sanitize(series)
        show_ids = self._get_show_ids()
        show_id = None

        # attempt with year
        if not show_id and year:
            logger.debug('Getting show id with year')
            show_id = show_ids.get('%s %d' % (series_sanitized, year))

        # attempt clean
        if not show_id:
            logger.debug('Getting show id')
            show_id = show_ids.get(series_sanitized)

        return show_id

    def get_episode_url(self, show_id, series, season, episode, year=None):
        """Get the url best matching show id for `series`, `season`, `episode` and `year`.

        :param int show_id: show id of the series
        :param str series: serie of the episode.
        :param int season: season of the episode.
        :param int episode: number of the episode.
        :param int year: year of the series.
        :return: the episode url, if found.
        :rtype: str

        """
        # get the page of the season of the show
        logger.info('Getting the page of show id %d, season %d', show_id, season)

        series_sanitized = sanitize(series)
        episode_url = None

        r = self.session.get(self.subtitles_url, params={'show': show_id, 'season': season}, timeout=10)
        r.raise_for_status()
        soup = ParserBeautifulSoup(r.content, ['lxml', 'html.parser'])

        # loop over episodes rows
        for html_episode in soup.select('td > a[href*="/episodes/"]'):
            title = sanitize(html_episode.get_text())

            # attempt series with year
            if sanitize('{} {} {}x{:02d}'.format(series_sanitized, year, season, episode)) in title:
                episode_url = 'https://' + html_episode['href'][2:]
                logger.debug('Subtitle found for %s, season: %d, episode: %d. URL: %s', series, season, episode,
                             episode_url)
                break
            elif sanitize('{} {}x{:02d}'.format(series_sanitized, season, episode)) in title:
                episode_url = 'https://' + html_episode['href'][2:]
                logger.debug('Subtitle found for %s, season: %d, episode: %d. URL: %s', series, season, episode,
                             episode_url)
                break

        return episode_url

    def query(self, series, season, episode, year=None):
        # get the show id
        show_id = self.get_show_id(series, year)
        if show_id is None:
            logger.error('No show id found for %s (%r)', series, year)
            return []

        # get the episode url
        episode_url = self.get_episode_url(show_id, series, season, episode, year)
        if episode_url is None:
            logger.error('No episode url found for %s, season %d, episode %d', series, season, episode)
            return []

        # get the page of the episode of the show
        r = self.session.get(episode_url, timeout=10)
        r.raise_for_status()
        soup = ParserBeautifulSoup(r.content, ['lxml', 'html.parser'])

        # get episode title
        title_pattern = re.compile('Subt.+tulos de {}(.+){}x{:02d} - (.+)'.format(series, season, episode).lower())
        title = title_pattern.search(soup.select('#cabecera-subtitulo')[0].get_text().strip().lower()).group(2)

        # loop over subtitle rows
        subtitles = []

        for sub in soup.find_all('div', attrs={'id': re.compile('version([0-9]+)')}):
            # read the release subtitle
            release = sanitize_release_group(release_pattern.search(sub.find('p', class_='title-sub')
                                                                    .contents[2]).group(1))

            for html_language in sub.select('ul.sslist'):
                language = Language.fromtusubtitulo(html_language.find_next('b').get_text().strip())
                hearing_impaired = False

                # modify spanish latino subtitle language to only spanish and set hearing_impaired = True
                # because if exists spanish and spanish latino subtitle for the same episode, the score will be
                # higher with spanish subtitle. Spanish subtitle takes priority.
                if language == Language('spa', 'MX'):
                    language = Language('spa')
                    hearing_impaired = True

                # ignore incomplete subtitles
                status = sanitize(html_language.find_next('li', class_=re.compile('li-estado')).get_text())
                if status != 'completado':
                    logger.debug('Ignoring subtitle with status %s', status)
                    continue

                # get the most updated version of the subtitle and if it doesn't exist get the original version
                html_status = html_language.select('a[href^="updated/"]')
                if len(html_status) == 0:
                    html_status = html_language.select('a[href^="original/"]')

                subtitle_url = self.server_url + html_status[0]['href']
                subtitle = TuSubtituloSubtitle(language, hearing_impaired, episode_url, series, season, episode, title,
                                               year, release, subtitle_url)
                logger.debug('Found subtitle %r', subtitle)
                subtitles.append(subtitle)

        return subtitles

    def list_subtitles(self, video, languages):
        return [s for s in self.query(video.series, video.season, video.episode,
                                      video.year)
                if s.language in languages]

    def download_subtitle(self, subtitle):
        # download the subtitle
        logger.info('Downloading subtitle %s', subtitle.download_link)
        r = self.session.get(subtitle.download_link, headers={'Referer': subtitle.page_link},
                             timeout=10)
        r.raise_for_status()

        subtitle.content = fix_line_ending(r.content)
