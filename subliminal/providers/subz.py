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
from ..matches import guess_matches
from ..subtitle import SUBTITLE_EXTENSIONS, Subtitle, fix_line_ending
from ..utils import sanitize
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

    @property
    def info(self):
        return self.version or self.download_link

    def get_matches(self, video):
        matches = set()
        video_type = None

        guess = {
            'year': self.year,
            'release_group': self.version
        }

        # episode
        if isinstance(video, Episode):
            video_type = 'episode'

            guess.update({
                'title': self.series,
                'season': self.season,
                'episode': self.episode,
                'episode_title': self.title
            })
        # movie
        elif isinstance(video, Movie):
            video_type = 'movie'

            guess.update({
                'title': self.title
            })

        # other properties
        matches |= guess_matches(video, guess)
        matches |= guess_matches(video, guessit(self.version, {'type': video_type}), partial=True)

        return matches


class SubzProvider(Provider):
    """Subz Provider."""
    languages = {Language.fromalpha2('el')}
    server_url = 'https://subz.xyz'
    sign_in_url = '/sessions'
    sign_out_url = '/logout'
    search_url = '/typeahead/{}'
    episode_link = '/series/{show_id}/seasons/{season:d}/episodes/{episode:d}'
    movie_link = '/movies/{}'
    subtitle_class = SubzSubtitle

    def __init__(self):
        self.logged_in = False
        self.session = None

    def initialize(self):
        self.session = Session()
        self.session.headers['User-Agent'] = 'Subliminal/{}'.format(__short_version__)

    def terminate(self):
        self.session.close()

    def get_show_links(self, title, year=None, is_episode=True):
        """Get the matching show links for `title` and `year`.

        First search in the result of :meth:`_get_show_suggestions`.

        :param title: show title.
        :param year: year of the show, if any.
        :type year: int
        :param is_episode: if the search is for episode.
        :type is_episode: bool
        :return: the show links, if found.
        :rtype: list of str

        """
        title = sanitize(title)
        suggestions = self._get_suggestions(title, is_episode)

        show_links = []
        for suggestion in suggestions:
            if sanitize(suggestion['title']) == title or \
                    (year and sanitize(suggestion['title']) == '{title} {year}'.format(title=title, year=year)):
                logger.debug('Getting show id')
                show_links.append(suggestion['link'].split('/')[-1])

        return show_links

    @region.cache_on_arguments(expiration_time=SHOW_EXPIRATION_TIME, should_cache_fn=lambda value: value)
    def _get_suggestions(self, title, is_episode=True):
        """Search the show or movie id from the `title`.

        :param str title: title of the show.
        :param is_episode: if the search is for episode.
        :type is_episode: bool
        :return: the show suggestions found.
        :rtype: list of dict

        """
        # make the search
        logger.info('Searching show ids with %r', title)
        r = self.session.get(self.server_url + self.search_url.format(title), timeout=10)
        r.raise_for_status()

        if not r.content:
            logger.debug('No data returned from provider')
            return []

        show_type = 'series' if is_episode else 'movie'
        parsed_suggestions = [s for s in json.loads(r.text) if 'type' in s and s['type'] == show_type]
        logger.debug('Found suggestions: %r', parsed_suggestions)

        return parsed_suggestions

    def query(self, show_id, series, season, episode, title):
        # get the season list of the show
        logger.info('Getting the subtitle list of show id %s', show_id)
        is_episode = False
        if all((show_id, season, episode)):
            is_episode = True
            page_link = self.server_url + self.episode_link.format(show_id=show_id, season=season, episode=episode)
        elif all((show_id, title)):
            page_link = self.server_url + self.movie_link.format(show_id)
        else:
            return []

        r = self.session.get(page_link, timeout=10)
        r.raise_for_status()

        if not r.content:
            logger.debug('No data returned from provider')
            return []

        soup = ParserBeautifulSoup(r.content, ['lxml', 'html.parser'])

        year = None
        if not is_episode:
            year = int(soup.select_one('span.year').text)
        show_title = str(soup.select_one('#summary-wrapper > div.summary h1').contents[0]).strip()

        subtitles = []
        # loop over episode rows
        for subs_tag in soup.select('div[id="subtitles"] tr[data-id]'):
            # read common info
            version = subs_tag.find('td', {'class': 'name'}).text
            download_link = subs_tag.find('a', {'class': 'btn-success'})['href'].strip('\'')

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
                                               episode_num, episode_title, year, version, download_link)
            # read the movie info
            else:
                subtitle = self.subtitle_class(Language.fromalpha2('el'), page_link, None, None, None, show_title,
                                               year, version, download_link)

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

        show_links = None
        for title in titles:
            show_links = self.get_show_links(title, video.year, isinstance(video, Episode))
            if show_links is not None and len(show_links) > 0:
                break

        subtitles = []
        # query for subtitles with the show_id
        for show_links in show_links:
            if isinstance(video, Episode):
                subtitles += [s for s in self.query(show_links, video.series, video.season, video.episode, video.title)
                              if s.language in languages and s.season == video.season and s.episode == video.episode]
            elif isinstance(video, Movie):
                subtitles += [s for s in self.query(show_links, None, None, None, video.title)
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
