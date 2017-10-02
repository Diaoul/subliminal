# -*- coding: utf-8 -*-
import bisect
import io
import logging
from urllib.parse import urlencode
import zipfile

from babelfish import Language
from guessit import guessit
from requests import Session

from . import Provider
from .. import __short_version__
from ..exceptions import AuthenticationError, ConfigurationError, ProviderError
from ..subtitle import Subtitle, fix_line_ending, guess_matches
from ..utils import sanitize
from ..video import Episode, Movie

logger = logging.getLogger(__name__)


class SubsCenterSubtitle(Subtitle):
    """SubsCenter Subtitle."""
    provider_name = 'subscenter'

    def __init__(self, language, page_link, series, season, episode, title, subtitle_id, subtitle_key,
                 releases):
        super(SubsCenterSubtitle, self).__init__(language, page_link=page_link)
        self.series = series
        self.season = season
        self.episode = episode
        self.title = title
        self.subtitle_id = subtitle_id
        self.subtitle_key = subtitle_key
        self.downloaded = 0
        self.releases = releases

    @property
    def id(self):
        return str(self.subtitle_id)

    def get_matches(self, video):
        matches = set()

        # episode
        if isinstance(video, Episode):
            # series
            if video.series and sanitize(self.series) == sanitize(video.series):
                matches.add('series')
            # season
            if video.season and self.season == video.season:
                matches.add('season')
            # episode
            if video.episode and self.episode == video.episode:
                matches.add('episode')
            # guess
            for release in self.releases:
                matches |= guess_matches(video, guessit(release, {'type': 'episode'}))
        # movie
        elif isinstance(video, Movie):
            # guess
            for release in self.releases:
                matches |= guess_matches(video, guessit(release, {'type': 'movie'}))

        # title
        if video.title and sanitize(self.title) == sanitize(video.title):
            matches.add('title')

        return matches


class SubsCenterProvider(Provider):
    """SubsCenter Provider."""
    languages = {Language.fromalpha2(l) for l in ['he']}
    server_url = 'http://www.cinemast.org/he/cinemast/api/'
    subtitle_class = SubsCenterSubtitle

    default_username = 'subliminal@gmail.com'
    default_password = 'subliminal'

    def __init__(self, username=None, password=None):
        if any((username, password)) and not all((username, password)):
            raise ConfigurationError('Username and password must be specified')

        self.session = None
        self.username = username or self.default_username
        self.password = password or self.default_password
        self.user_id = None
        self.token = None
        self.session = None

    def initialize(self):
        self.session = Session()
        self.session.headers['User-Agent'] = 'Subliminal/{}'.format(__short_version__)

        # login
        if self.username and self.password:
            logger.debug('Logging in')
            url = self.server_url + 'login/'

            # actual login
            data = {'username': self.username, 'password': self.password}
            r = self.session.post(url, data=urlencode(data), allow_redirects=False, timeout=10)

            if r.status_code != 200:
                raise AuthenticationError(self.username)

            try:
                result = r.json()
                if 'token' not in result:
                    raise AuthenticationError(self.username)

                logger.info('Logged in')
                self.user_id = r.json().get('user')
                self.token = r.json().get('token')
            except ValueError:
                raise AuthenticationError(self.username)

    def terminate(self):
        # logout
        if self.token or self.user_id:
            logger.info('Logged out')
            self.token = None
            self.user_id = None

        self.session.close()

    def query(self, title, season=None, episode=None, year=None):
        query = {
            'q': title,
            'user': self.user_id,
            'token': self.token
        }

        # episode
        if season and episode:
            query['type'] = 'series'
            query['season'] = season
            query['episode'] = episode
        else:
            query['type'] = 'movies'
            if year:
                query['year_start'] = year - 1
                query['year_end'] = year

        # get the list of subtitles
        logger.debug('Getting the list of subtitles')
        url = self.server_url + 'search/'
        r = self.session.post(url, data=urlencode(query))
        r.raise_for_status()

        try:
            results = r.json()
        except ValueError:
            return {}

        # loop over results
        subtitles = {}
        for group_data in results.get('data', []):
            # create page link
            slug_name = group_data.get('name_en').lower().replace(' ', '-').replace('\'', '').replace('"', '')
            if query['type'] == 'series':
                page_link = self.server_url + 'subtitle/series/{}/{}/{}/'.format(slug_name, season, episode)
            else:
                page_link = self.server_url + 'subtitle/movie/{}/'.format(slug_name)

            # go over each language
            for language_code, subtitles_data in group_data.get('subtitles', {}).items():
                for subtitle_item in subtitles_data:
                    # read the item
                    language = Language.fromalpha2(language_code)
                    subtitle_id = subtitle_item['id']
                    subtitle_key = subtitle_item['key']
                    release = subtitle_item['version']

                    # add the release and increment downloaded count if we already have the subtitle
                    if subtitle_id in subtitles:
                        logger.debug('Found additional release %r for subtitle %r', release, subtitle_id)
                        bisect.insort_left(subtitles[subtitle_id].releases, release)  # deterministic order
                        subtitles[subtitle_id].downloaded += 1
                        continue

                    # otherwise create it
                    subtitle = self.subtitle_class(language, page_link, title, season, episode, title, subtitle_id,
                                                   subtitle_key, [release])
                    logger.debug('Found subtitle %r', subtitle)
                    subtitles[subtitle_id] = subtitle

        return subtitles.values()

    def list_subtitles(self, video, languages):
        season = episode = None
        title = video.title

        if isinstance(video, Episode):
            title = video.series
            season = video.season
            episode = video.episode

        return [s for s in self.query(title, season, episode) if s.language in languages]

    def download_subtitle(self, subtitle):
        # download
        url = self.server_url + 'subtitle/download/{}/'.format(subtitle.language.alpha2)
        params = {
            'v': subtitle.releases[0],
            'key': subtitle.subtitle_key,
            'sub_id': subtitle.subtitle_id
        }
        data = {
            'user': self.user_id,
            'token': self.token
        }
        r = self.session.post(url, data=urlencode(data), params=params, timeout=10)
        r.raise_for_status()

        # open the zip
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            # remove some filenames from the namelist
            namelist = [n for n in zf.namelist() if not n.endswith('.txt')]
            if len(namelist) > 1:
                raise ProviderError('More than one file to unzip')

            subtitle.content = fix_line_ending(zf.read(namelist[0]))
