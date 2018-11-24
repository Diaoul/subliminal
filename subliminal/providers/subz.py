# -*- coding: utf-8 -*-
import io
import json
import logging
import os

import rarfile
import re
import zipfile

from babelfish import Language
from guessit import guessit
from requests import Session

from . import ParserBeautifulSoup, Provider
from .. import __short_version__
from ..cache import SHOW_EXPIRATION_TIME, region
from ..exceptions import AuthenticationError, ConfigurationError
from ..score import get_equivalent_release_groups
from ..subtitle import SUBTITLE_EXTENSIONS, Subtitle, fix_line_ending, guess_matches
from ..utils import sanitize, sanitize_release_group
from ..video import Episode, Movie

logger = logging.getLogger(__name__)

episode_re = re.compile(r'^S(\d{2})E(\d{2})$')


class SubzSubtitle(Subtitle):
    """Subz Subtitle."""
    provider_name = 'subz'

    def __init__(self, language, page_link, series, season, episode, title, year, version, download_link):
        super(SubzSubtitle, self).__init__(language, page_link=page_link)
        self.series = series
        self.season = season
        self.episode = episode
        self.title = title
        self.year = year
        self.version = version
        self.download_link = download_link
        self.hearing_impaired = None
        self.encoding = 'windows-1253'

    @property
    def id(self):
        return self.download_link

    def get_matches(self, video):
        matches = set()
        video_type = None

        # episode
        if isinstance(video, Episode):
            video_type = 'episode'
            # series name
            if video.series and sanitize(self.series) in (
                    sanitize(name) for name in [video.series] + video.alternative_series):
                matches.add('series')
            # season
            if video.season and self.season == video.season:
                matches.add('season')
            # episode
            if video.episode and self.episode == video.episode:
                matches.add('episode')
            # title of the episode
            if video.title and sanitize(self.title) == sanitize(video.title):
                matches.add('title')
            # year
            if video.original_series and self.year is None or video.year and video.year == self.year:
                matches.add('year')
        # movie
        elif isinstance(video, Movie):
            video_type = 'movie'
            # title
            if video.title and (sanitize(self.title) in (
                    sanitize(name) for name in [video.title] + video.alternative_titles)):
                matches.add('title')
            # year
            if video.year and self.year == video.year:
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
        if video.source and self.version and sanitize(video.source) in sanitize(self.version):
            matches.add('source')
        # other properties
        matches |= guess_matches(video, guessit(self.version, {'type': video_type}), partial=True)

        return matches


class SubzProvider(Provider):
    """Subz Provider."""
    languages = {Language.fromalpha2('el')}
    server_url = 'https://subz.xyz'
    sign_in_url = '/sessions'
    sign_out_url = '/logout'
    search_url = '/typeahead/%s'
    episode_link = '/series/%s/seasons/%d/episodes/%d'
    movie_link = '/movies/%s'
    subtitle_class = SubzSubtitle

    def __init__(self, username=None, password=None):
        if any((username, password)) and not all((username, password)):
            raise ConfigurationError('Username and password must be specified')

        self.username = username
        self.password = password
        self.logged_in = False
        self.session = None

    def initialize(self):
        self.session = Session()
        self.session.headers['User-Agent'] = 'Subliminal/%s' % __short_version__

        # login
        if all((self.username, self.password)):
            logger.info('Logging in')
            r = self.session.get(self.server_url + '/login')
            r.raise_for_status()

            if not r.content:
                logger.debug('No data returned from provider')
                return

            soup = ParserBeautifulSoup(r.content, ['lxml', 'html.parser'])
            token = soup.select_one('form.form-signin > input[name="_token"]')['value']

            data = {'_token': token,
                    'username': self.username,
                    'password': self.password}
            r = self.session.post(self.server_url + self.sign_in_url, data,
                                  headers={'Referer': self.server_url + '/login'}, allow_redirects=False, timeout=10)

            if r.status_code != 302 or r.url != self.server_url:
                raise AuthenticationError(self.username)

            logger.debug('Logged in')
            self.logged_in = True

    def terminate(self):
        # logout
        if self.logged_in:
            logger.info('Logging out')
            r = self.session.get(self.server_url + self.sign_out_url, timeout=10)
            r.raise_for_status()
            logger.debug('Logged out')
            self.logged_in = False

        self.session.close()

    def get_show_ids(self, title, year=None, is_episode=True, country_code=None):
        """Get the best matching show id for `series`, `year` and `country_code`.

        First search in the result of :meth:`_get_show_suggestions`.

        :param title: show title.
        :param year: year of the show, if any.
        :type year: int
        :param is_episode: if the search is for episode.
        :type is_episode: bool
        :param country_code: country code of the show, if any.
        :type country_code: str
        :return: the show id, if found.
        :rtype: str

        """
        title_sanitized = sanitize(title).lower()
        show_ids = self._get_suggestions(title, is_episode)

        matched_show_ids = []
        for show in show_ids:
            show_id = None
            # attempt with country
            if not show_id and country_code:
                logger.debug('Getting show id with country')
                show_id = show['link'].split('/')[-1] if sanitize(show['title']) == '%s %s' % (
                    title_sanitized, country_code.lower()) else None

            # attempt with year
            if not show_id and year:
                logger.debug('Getting show id with year')
                show_id = show['link'].split('/')[-1] if sanitize(show['title']) == '%s %d' % (
                    title_sanitized, year) else None

            # attempt clean
            if not show_id:
                logger.debug('Getting show id')
                show_id = show['link'].split('/')[-1] if sanitize(show['title']) == title_sanitized else None

            if show_id:
                matched_show_ids.append(show_id)

        return matched_show_ids

    @region.cache_on_arguments(expiration_time=SHOW_EXPIRATION_TIME)
    def _get_suggestions(self, title, is_episode=True):
        """Search the show or movie id from the `title` and `year`.

        :param str title: title of the show.
        :param is_episode: if the search is for episode.
        :type is_episode: bool
        :return: the show suggestions found.
        :rtype: dict

        """
        # make the search
        logger.info('Searching show ids with %r', title)
        r = self.session.get(self.server_url + self.search_url % title, timeout=10)
        r.raise_for_status()

        if not r.content:
            logger.debug('No data returned from provider')
            return {}

        show_type = 'series' if is_episode else 'movie'
        parsed_suggestions = [s for s in json.loads(r.content) if 'type' in s and s['type'] == show_type]
        logger.debug('Found suggestions: %r', parsed_suggestions)

        return parsed_suggestions

    def query(self, show_id, series, season, episode, title):
        # get the season list of the show
        logger.info('Getting the subtitle list of show id %s', show_id)
        is_episode = False
        if all((show_id, season, episode)):
            is_episode = True
            page_link = self.server_url + self.episode_link % (show_id, season, episode)
        elif all((show_id, title)):
            page_link = self.server_url + self.movie_link % show_id
        else:
            return []

        r = self.session.get(page_link, timeout=10)
        r.raise_for_status()

        if not r.content:
            logger.debug('No data returned from provider')
            return []

        soup = ParserBeautifulSoup(r.content, ['lxml', 'html.parser'])

        year_num = None
        if not is_episode:
            year_num = int(soup.select_one('span.year').text)
        show_title = str(soup.select_one('#summary-wrapper > div.summary h1').contents[0]).strip()

        subtitles = []
        # loop over episode rows
        for subtitle in soup.select('div[id="subtitles"] tr[data-id]'):
            # read common info
            version = subtitle.find('td', {'class': 'name'}).text
            download_link = subtitle.find('a', {'class': 'btn-success'})['href'].strip('\'')

            # read the episode info
            if is_episode:
                episode_numbers = soup.select_one('#summary-wrapper > div.container.summary span.main-title-sxe').text
                season_num = None
                episode_num = None
                matches = episode_re.match(episode_numbers.strip())
                if matches:
                    season_num = int(matches.group(1))
                    episode_num = int(matches.group(2))

                episode_title = soup.select_one('#summary-wrapper > div.container.summary span.main-title').text

                subtitle = self.subtitle_class(Language.fromalpha2('el'), page_link, show_title, season_num,
                                               episode_num, episode_title, year_num, version, download_link)
            # read the movie info
            else:
                subtitle = self.subtitle_class(Language.fromalpha2('el'), page_link, None, None, None, show_title,
                                               year_num, version, download_link)

            logger.debug('Found subtitle %r', subtitle)
            subtitles.append(subtitle)

        return subtitles

    def list_subtitles(self, video, languages):
        # lookup show_id
        if isinstance(video, Episode):
            titles = [video.series] + video.alternative_series
        elif isinstance(video, Movie):
            titles = [video.title] + video.alternative_titles
        else:
            titles = []

        show_ids = None
        for title in titles:
            show_ids = self.get_show_ids(title, video.year, isinstance(video, Episode))
            if show_ids is not None:
                break

        subtitles = []
        # query for subtitles with the show_id
        for show_id in show_ids:
            if isinstance(video, Episode):
                subtitles += [s for s in self.query(show_id, video.series, video.season, video.episode, video.title)
                              if s.language in languages and s.season == video.season and s.episode == video.episode]
            elif isinstance(video, Movie):
                subtitles += [s for s in self.query(show_id, None, None, None, video.title)
                              if s.language in languages and s.year == video.year]

        return subtitles

    def download_subtitle(self, subtitle):
        if isinstance(subtitle, SubzSubtitle):
            # download the subtitle
            logger.info('Downloading subtitle %r', subtitle)
            r = self.session.get(subtitle.download_link, headers={'Referer': subtitle.page_link}, timeout=10)
            r.raise_for_status()

            if not r.content:
                logger.debug('Unable to download subtitle. No data returned from provider')
                return

            archive = _get_archive(r.content)

            subtitle_content = _get_subtitle_from_archive(archive)
            if subtitle_content:
                subtitle.content = fix_line_ending(subtitle_content)
            else:
                logger.debug('Could not extract subtitle from %r', archive)


def _get_archive(content):
    # open the archive
    archive_stream = io.BytesIO(content)
    archive = None
    if rarfile.is_rarfile(archive_stream):
        logger.debug('Identified rar archive')
        archive = rarfile.RarFile(archive_stream)
    elif zipfile.is_zipfile(archive_stream):
        logger.debug('Identified zip archive')
        archive = zipfile.ZipFile(archive_stream)

    return archive


def _get_subtitle_from_archive(archive):
    for name in archive.namelist():
        # discard hidden files
        if os.path.split(name)[-1].startswith('.'):
            continue

        # discard non-subtitle files
        if not name.lower().endswith(SUBTITLE_EXTENSIONS):
            continue

        return archive.read(name)

    return None
