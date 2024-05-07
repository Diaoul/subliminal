from __future__ import annotations

import io
import json
import logging

from babelfish import Language, language_converters
from guessit import guessit
from requests import Session
from zipfile import ZipFile

from . import Provider, SecLevelOneTLSAdapter
from ..exceptions import ProviderError
from ..matches import guess_matches
from ..subtitle import Subtitle, fix_line_ending
from ..video import Episode


logger = logging.getLogger(__name__)


class PodnapisiSubtitle(Subtitle):
    """Podnapisi Subtitle."""
    provider_name = 'podnapisi'

    def __init__(self, language, hearing_impaired, page_link, pid, releases, title, season=None, episode=None,
                 year=None):
        super().__init__(language, hearing_impaired=hearing_impaired, page_link=page_link)
        self.pid = pid
        self.releases = releases
        self.title = title
        self.season = season
        self.episode = episode
        self.year = year

    @property
    def id(self):
        return self.pid

    @property
    def info(self):
        return ' '.join(self.releases) or self.pid

    def get_matches(self, video):
        matches = guess_matches(video, {
            'title': self.title,
            'year': self.year,
            'season': self.season,
            'episode': self.episode
        })

        video_type = 'episode' if isinstance(video, Episode) else 'movie'
        for release in self.releases:
            matches |= guess_matches(video, guessit(release, {'type': video_type}))

        return matches


class PodnapisiProvider(Provider):
    """Podnapisi Provider."""
    languages = ({Language('por', 'BR'), Language('srp', script='Latn')} |
                 {Language.fromalpha2(l) for l in language_converters['alpha2'].codes})
    server_url = 'https://www.podnapisi.net/subtitles/'
    subtitle_class = PodnapisiSubtitle

    def __init__(self):
        self.session = None

    def initialize(self):
        self.session = Session()
        self.session.mount('https://', SecLevelOneTLSAdapter())
        self.session.headers['User-Agent'] = self.user_agent
        self.session.headers['Accept'] = 'application/json'

    def terminate(self):
        self.session.close()

    def query(self, language, keyword, season=None, episode=None, year=None):
        # set parameters, see http://www.podnapisi.net/forum/viewtopic.php?f=62&t=26164#p212652
        params = {'keywords': keyword, 'language': str(language)}
        is_episode = False
        if season is not None and episode:
            is_episode = True
            params['seasons'] = season
            params['episodes'] = episode
            params['movie_type'] = ['tv-series', 'mini-series']
        else:
            params['movie_type'] = 'movie'
        if year:
            params['year'] = year

        # loop over paginated results
        logger.info('Searching subtitles %r', params)
        subtitles = []
        pids = set()
        while True:
            # query the server
            r = self.session.get(self.server_url + 'search/advanced', params=params, timeout=10)
            r.raise_for_status()
            result = json.loads(r.text)

            # loop over subtitles
            for data in result['data']:
                # read xml elements
                pid = data['id']
                # ignore duplicates, see http://www.podnapisi.net/forum/viewtopic.php?f=62&t=26164&start=10#p213321
                if pid in pids:
                    logger.debug('Ignoring duplicate %r', pid)
                    continue

                if is_episode and data['movie']['type'] == 'movie':
                    logger.error('Wrong type detected: movie for episode')
                    continue

                language = Language.fromietf(data['language'])
                hearing_impaired = 'hearing_impaired' in data['flags']
                page_link = data['url']
                releases = data['releases'] + data['custom_releases']
                title = data['movie']['title']
                season = int(data['movie']['episode_info'].get('season')) if is_episode else None
                episode = int(data['movie']['episode_info'].get('episode')) if is_episode else None
                year = int(data['movie']['year'])

                if is_episode:
                    subtitle = self.subtitle_class(language, hearing_impaired, page_link, pid, releases, title,
                                                   season=season, episode=episode, year=year)
                else:
                    subtitle = self.subtitle_class(language, hearing_impaired, page_link, pid, releases, title,
                                                   year=year)

                logger.debug('Found subtitle %r', subtitle)
                subtitles.append(subtitle)
                pids.add(pid)

            # stop on last page
            if int(result['page']) >= int(result['all_pages']):
                break

            # increment current page
            params['page'] = int(result['page']) + 1
            logger.debug('Getting page %d', params['page'])

        return subtitles

    def list_subtitles(self, video, languages):
        season = episode = None
        if isinstance(video, Episode):
            titles = [video.series] + video.alternative_series
            season = video.season
            episode = video.episode
        else:
            titles = [video.title] + video.alternative_titles

        for title in titles:
            subtitles = [s for l in languages for s in
                         self.query(l, title, season=season, episode=episode, year=video.year)]
            if subtitles:
                return subtitles

        return []

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
