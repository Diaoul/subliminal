# -*- coding: utf-8 -*-
import io
import json
import logging
import re
import zipfile

from babelfish import Language
import guessit
from requests import Session

from . import Provider
from .. import __version__
from ..exceptions import AuthenticationError, ProviderError, ConfigurationError
from ..subtitle import Subtitle, fix_line_ending, guess_matches
from ..video import Episode, Movie

logger = logging.getLogger(__name__)


class SubsCenterSubtitle(Subtitle):

    _GUESSIT_EXT = '.mkv'

    provider_name = 'subscenter'

    def __init__(self, language, series, season, episode, title, release_name, kind, hearing_impaired,
                 download_link, page_link):
        super(SubsCenterSubtitle, self).__init__(language, hearing_impaired, page_link)
        self.series = series
        self.season = season
        self.episode = episode
        self.title = title
        self.release_name = release_name
        self.kind = kind
        self.download_link = download_link

    @property
    def id(self):
        return self.download_link

    def get_matches(self, video, hearing_impaired=False):
        matches = super(SubsCenterSubtitle, self).get_matches(video, hearing_impaired=hearing_impaired)

        # episode
        if isinstance(video, Episode) and self.kind == 'episode':
            # series
            if video.series and self.series.lower() == video.series.lower():
                matches.add('series')
            # season
            if video.season and self.season == video.season:
                matches.add('season')
            # episode
            if video.episode and self.episode == video.episode:
                matches.add('episode')
            # guess
            matches |= guess_matches(video, guessit.guess_episode_info(self.release_name + self._GUESSIT_EXT))
        # movie
        elif isinstance(video, Movie) and self.kind == 'movie':
            # guess
            matches |= guess_matches(video, guessit.guess_movie_info(self.release_name + self._GUESSIT_EXT))
        else:
            logger.info('%r is not a valid movie_kind for %r', self.kind, video)
            return matches
        # title
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
        # login
        if self.username is not None and self.password is not None:
            logger.debug('Logging in')
            url = self.server + 'subscenter/accounts/login/'
            # Retrieve CSRF token first.
            self.session.get(url)
            csrf_token = self.session.cookies['csrftoken']
            data = {'username': self.username, 'password': self.password,
                    'next': '/he/', 'csrfmiddlewaretoken': csrf_token}
            r = self.session.post(url, data, timeout=10, allow_redirects=False)
            if r.status_code == 302:
                logger.info('Logged in')
                self.logged_in = True
            else:
                raise AuthenticationError(self.username)

    def terminate(self):
        # logout
        if self.logged_in:
            r = self.session.get(self.server + 'subscenter/accounts/logout/', timeout=10)
            logger.info('Logged out')
            if r.status_code != 200:
                raise ProviderError('Request failed with status code %d' % r.status_code)
            self.logged_in = False
        self.session.close()

    @staticmethod
    def slugify(string):
        new_string = string.replace(' ', '-').replace("'", '').replace(':', '').lower()
        # We remove multiple spaces by using this regular expression.
        return re.sub('-+', '-', new_string)

    def query(self, languages=None, series=None, season=None, episode=None, title=None):
        # Converts the title to Subscenter format by replacing whitespaces and removing specific chars.
        if series and season and episode:
            # Search for a TV show.
            kind = 'episode'
            slugified_series = self.slugify(series)
            url = self.server + 'cinemast/data/series/sb/' + slugified_series + '/' + str(season) + '/' + \
                str(episode) + '/'
            page_link = self.server + 'subtitle/series/' + slugified_series + '/' + str(season) + '/' + \
                str(episode) + '/'
        elif title:
            # Search for a movie.
            kind = 'movie'
            slugified_title = self.slugify(title)
            url = self.server + 'cinemast/data/movie/sb/' + slugified_title + '/'
            page_link = self.server + 'subtitle/movie/' + slugified_title + '/'
        else:
            raise ValueError('One or more parameters are missing')
        logger.debug('Searching subtitles %r', {'title': title, 'season': season, 'episode': episode})
        response = self.session.get(url)
        if response.status_code != 200:
            raise ProviderError('Request failed with status code %d' % response.status_code)

        subtitles = []
        response_json = json.loads(response.content.decode('UTF-8'))
        for lang, lang_json in response_json.items():
            lang_obj = Language.fromalpha2(lang)
            if lang_obj in self.languages and lang in languages:
                for group_data in lang_json.values():
                    for quality in group_data.values():
                        for sub in quality.values():
                            release = sub.get('subtitle_version')
                            download_link = self.server + 'subtitle/download/' + lang + '/' + str(sub.get('id')) + \
                                '/?v=' + release + '&key=' + str(sub.get('key'))
                            subtitles.append(SubsCenterSubtitle(lang_obj, series, season,
                                                                episode, title, release, kind,
                                                                bool(sub.get('hearing_impaired', 0)),
                                                                download_link, page_link))
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
        r = self.session.get(subtitle.download_link, timeout=10, headers={'Referer': subtitle.page_link})
        if r.status_code != 200:
            raise ProviderError('Request failed with status code %d' % r.status_code)
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            names_list = [x for x in zf.namelist() if not x.endswith('.txt')]
            if len(names_list) > 1:
                raise ProviderError('More than one file to unzip')
            subtitle.content = fix_line_ending(zf.read(names_list[0]))
