# -*- coding: utf-8 -*-
import io
import json
import logging
from zipfile import ZipFile

from babelfish import Language
from guessit import guessit
from requests import Session
from six.moves import urllib

from . import Provider
from ..cache import EPISODE_EXPIRATION_TIME, region
from ..exceptions import ProviderError
from ..matches import guess_matches
from ..subtitle import Subtitle, fix_line_ending
from ..video import Episode

logger = logging.getLogger(__name__)

# Mostly a copy of the logic from `legendastv.py`. TODO:
# [ ] Check tests
# [ ] Add some logging lines
# How to quick test:
# cd ~/.local/lib/python3.8/site-packages/subliminal
# mv providers/argenteam.py{,.old}
# ln -s ~/subliminal/subliminal/providers/argenteam.py providers/argenteam.py
# touch Little.Miss.Sunshine.2006.720p.BluRay.x264.YIFY.mp4
# touch "Curb Your Enthusiasm S11E02 720p HEVC x265-MeGusta[eztv.re].mkv"
# subliminal --debug download --language es --provider argenteam Curb\ Your\ Enthusiasm\ S11E02\ 720p\ HEVC\ x265-MeGusta\[eztv.re\].mkv

class ArgenteamSubtitle(Subtitle):
    provider_name = 'argenteam'

    def __init__(self, language, download_link, type, title, year, season, episode, release, version):
        super(ArgenteamSubtitle, self).__init__(language, download_link)
        self.download_link = download_link
        self.type = type
        self.title = title
        self.year = year
        self.season = season
        self.episode = episode
        self.release = release
        self.version = version

    @property
    def id(self):
        return self.download_link

    @property
    def info(self):
        return urllib.parse.unquote(self.download_link.rsplit('/')[-1])

    def get_matches(self, video):
        if isinstance(video, Episode) and self.type == 'episode':
            matches = guess_matches(video, {
                'title': self.title,
                'season': self.season,
                'episode': self.episode,
                'release_group': self.version
            })
        else:
            matches = guess_matches(video, {
                'title': self.title,
                'year': self.year,
                'release_group': self.version
            })

        # resolution
        if video.resolution and self.version and video.resolution in self.version.lower():
            matches.add('resolution')

        if isinstance(video, Episode) and self.type == 'episode':
            matches |= guess_matches(video, guessit(self.version, {'type': 'episode'}), partial=True)
        else:
            matches |= guess_matches(video, guessit(self.version, {'type': 'movie'}))
        return matches

class ArgenteamProvider(Provider):
    provider_name = 'argenteam'
    language = Language.fromalpha2('es')
    languages = {language}
    server_url = "https://argenteam.net/api/v1/"
    subtitle_class = ArgenteamSubtitle

    def __init__(self):
        self.session = None

    def initialize(self):
        self.session = Session()
        self.session.headers['User-Agent'] = self.user_agent

    def terminate(self):
        self.session.close()

    def search_first_ocurrence(self, query_str):
        r = self.session.get(self.server_url + 'search', params={'q': query_str}, timeout=10)
        r.raise_for_status()
        results = json.loads(r.text)
        if results['total'] == 1:
            return results['results'][0]['id']

        logger.error('No media id found for %r', query_str)

    def query(self, language, title, season=None, episodes=None, year=None):
        query = '%s' % (title)
        r = self.session.get(self.server_url + 'search', params={'q': query}, timeout=10)
        r.raise_for_status()
        results = json.loads(r.text)
        search_first_ocurrence

    def get_media_by_id(self, endpoint, id):
        if id is None:
            return []
        response = self.session.get(self.server_url + endpoint, params={'id': id}, timeout=10)
        response.raise_for_status()
        content = json.loads(response.text)
        return content

    def list_subtitles(self, video, languages):
        season = None
        episode = []
        subtitles = []
        if isinstance(video, Episode):
            series = video.series
            season = video.season
            episode = video.episode
            query = '%s S%#02dE%#02d' % (series, season, episode)
            content = self.get_media_by_id('episode', self.search_first_ocurrence(query))
            for r in content['releases']:
                for s in r['subtitles']:
                    subtitle = self.subtitle_class(self.language, s['uri'], 'episode', series, video.year, season, episode, r['team'], r['tags'])
                    logger.debug('Found subtitle %r', subtitle)
                    subtitles.append(subtitle)
        else:
            title = video.title
            year = video.year
            query = '%s %s' % (title, year)
            content = self.get_media_by_id('movie', self.search_first_ocurrence(query))
            for r in content['releases']:
                for s in r['subtitles']:
                    subtitle = self.subtitle_class(self.language, s['uri'], 'movie', title, year, None, None, r['team'], r['tags'])
                    logger.debug('Found subtitle %r', subtitle)
                    subtitles.append(subtitle)

        return subtitles

    def download_subtitle(self, subtitle):
        # download as a zip
        logger.info('Downloading subtitle %r', subtitle)
        r = self.session.get(subtitle.download_link, timeout=10)
        r.raise_for_status()

        # open the zip
        with ZipFile(io.BytesIO(r.content)) as zf:
            if len(zf.namelist()) > 1:
                raise ProviderError('More than one file to unzip')

            subtitle.content = fix_line_ending(zf.read(zf.namelist()[0]))
