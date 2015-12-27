# -*- coding: utf-8 -*-
import io
import json
import logging
import zipfile

from babelfish import Language
import guessit
from requests import Session

from . import ParserBeautifulSoup, Provider
from .. import __version__
from ..cache import SHOW_EXPIRATION_TIME, region
from ..exceptions import AuthenticationError, ProviderError, ConfigurationError
from ..subtitle import Subtitle, fix_line_ending, guess_matches
from ..video import Episode, Movie

logger = logging.getLogger(__name__)


class SubsCenterSubtitle(Subtitle):

    _GUESSIT_EXT = '.mkv'

    provider_name = 'subscenter'

    def __init__(self, subtitle_id, subtitle_key, language, series, season, episode, title, release_name, kind,
                 hearing_impaired, page_link):
        super(SubsCenterSubtitle, self).__init__(language, hearing_impaired, page_link)
        self.subtitle_id = subtitle_id
        self.subtitle_key = subtitle_key
        self.series = series
        self.season = season
        self.episode = episode
        self.title = title
        self.release_name = release_name
        self.kind = kind

    @property
    def id(self):
        return self.subtitle_id

    def get_matches(self, video, hearing_impaired=False):
        matches = super(SubsCenterSubtitle, self).get_matches(video, hearing_impaired=hearing_impaired)

        # Episode.
        if isinstance(video, Episode) and self.kind == 'episode':
            # Series.
            if video.series and self.series.lower() == video.series.lower():
                matches.add('series')
            # Season.
            if video.season and self.season == video.season:
                matches.add('season')
            # Episode.
            if video.episode and self.episode == video.episode:
                matches.add('episode')
            # Guess.
            matches |= guess_matches(video, guessit.guess_episode_info(self.release_name + self._GUESSIT_EXT))
        # Movie.
        elif isinstance(video, Movie) and self.kind == 'movie':
            # Guess.
            matches |= guess_matches(video, guessit.guess_movie_info(self.release_name + self._GUESSIT_EXT))
        else:
            logger.info('%r is not a valid movie_kind for %r', self.kind, video)
            return matches
        # Title.
        if video.title and self.title and self.title.lower() == video.title.lower():
            matches.add('title')
        return matches


class SubsCenterProvider(Provider):

    languages = {Language.fromalpha2(l) for l in ['he', 'en']}
    server = 'http://subscenter.cinemast.com/he/'

    def __init__(self, username=None, password=None):
        if username is not None and password is None or username is None and password is not None:
            raise ConfigurationError('Username and password must be specified')
        self.username = username
        self.password = password
        self.session = None
        self.logged_in = False

    def initialize(self):
        self.session = Session()
        self.session.headers = {'User-Agent': 'Subliminal/%s' % __version__.split('-')[0]}
        # Login.
        if self.username is not None and self.password is not None:
            logger.debug('Logging in')
            url = self.server + 'subscenter/accounts/login/'
            # Retrieve CSRF token first.
            self.session.get(url)
            csrf_token = self.session.cookies['csrftoken']
            data = {'username': self.username, 'password': self.password, 'csrfmiddlewaretoken': csrf_token}
            r = self.session.post(url, data, timeout=10, allow_redirects=False)
            if r.status_code == 302:
                logger.info('Logged in')
                self.logged_in = True
            else:
                raise AuthenticationError(self.username)

    def terminate(self):
        # Logout.
        if self.logged_in:
            r = self.session.get(self.server + 'subscenter/accounts/logout/', timeout=10)
            r.raise_for_status()
            logger.info('Logged out')
            self.logged_in = False
        self.session.close()

    @region.cache_on_arguments(expiration_time=SHOW_EXPIRATION_TIME)
    def search_title_name(self, title, is_series):
        """
        Search the slugified title name for the given title.

        :param string title: The full title name to search for.
        :param is_series: If True, a series-related result will be returned.
        Else, a movie-related result will be returned.
        :return: The slugified title name, or a slugified guess if the search yielded no results.
        """
        # make the search
        logger.info('Searching title name for %r', title)
        r = self.session.get(self.server + 'subtitle/search/?q=' + title.lower().replace(' ', '+'), timeout=10)
        r.raise_for_status()

        # get the series out of the suggestions
        try:
            soup = ParserBeautifulSoup(r.content, ['lxml', 'html.parser'])
            for suggestion in soup.select(
                    'div#sitePart div#content div#processes div.movieProcess div.generalWindowRight a'):
                link_parts = suggestion.attrs['href'].split('/')
                slugified_title = link_parts[-2]
                if (is_series and link_parts[-3] == 'series') or (not is_series and link_parts[-3] == 'movie'):
                    logger.info('Found slugified title %r', slugified_title)
                    return slugified_title
        except UnicodeDecodeError:
            # If something went wrong with the parsing, ignore the results.
            pass
        logger.info('Could not find slugified title for %r.', title)

    def query(self, languages=None, series=None, season=None, episode=None, title=None):
        # Converts the title to Subscenter format by replacing whitespaces and removing specific chars.
        if series and season and episode:
            # Search for a TV show.
            kind = 'episode'
            slugified_series = self.search_title_name(series, True)
            url = self.server + 'cinemast/data/series/sb/' + slugified_series + '/' + str(season) + '/' + \
                str(episode) + '/'
            page_link = self.server + 'subtitle/series/' + slugified_series + '/' + str(season) + '/' + \
                str(episode) + '/'
        elif title:
            # Search for a movie.
            kind = 'movie'
            slugified_title = self.search_title_name(title, False)
            url = self.server + 'cinemast/data/movie/sb/' + slugified_title + '/'
            page_link = self.server + 'subtitle/movie/' + slugified_title + '/'
        else:
            raise ValueError('One or more parameters are missing')
        logger.debug('Searching subtitles %r', {'title': title, 'season': season, 'episode': episode})
        response = self.session.get(url)
        response.raise_for_status()
        subtitles = []
        response_json = json.loads(response.text)
        for lang, lang_json in response_json.items():
            lang_obj = Language.fromalpha2(lang)
            if lang_obj in self.languages and lang in languages:
                for group_data in lang_json.values():
                    for quality in group_data.values():
                        for sub in quality.values():
                            release = sub.get('subtitle_version')
                            subtitle_id = sub.get('id')
                            subtitle_key = sub.get('key')
                            # We don't want to add problematic subtitles.
                            if subtitle_id is not None and subtitle_key is not None:
                                subtitles.append(SubsCenterSubtitle(subtitle_id, subtitle_key, lang_obj, series,
                                                                    season, episode, title, release, kind,
                                                                    bool(sub.get('hearing_impaired', 0)), page_link))
        # Sort for results consistency.
        subtitles.sort(key=lambda x: x.subtitle_key)
        return subtitles

    def list_subtitles(self, video, languages):
        series = None
        season = None
        episode = None
        title = video.title
        if isinstance(video, Episode):
            series = video.series
            season = video.season
            episode = video.episode
        return self.query(languages, series, season, episode, title)

    def download_subtitle(self, subtitle):
        # Generate the download link based on the given subtitle's properties.
        download_link = '{0}subtitle/download/{1}/{2}/?v={3}&key={4}'.format(
            self.server, subtitle.language, subtitle.subtitle_id, subtitle.release_name, subtitle.subtitle_key)
        r = self.session.get(download_link, timeout=10, headers={'Referer': subtitle.page_link})
        r.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            names_list = [x for x in zf.namelist() if not x.endswith('.txt')]
            if len(names_list) > 1:
                raise ProviderError('More than one file to unzip')
            subtitle.content = fix_line_ending(zf.read(names_list[0]))
