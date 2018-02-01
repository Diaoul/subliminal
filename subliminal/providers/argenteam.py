# -*- coding: utf-8 -*-
import io
import json
import logging
from zipfile import ZipFile

from babelfish import Language
from requests import Session

from . import Provider
from .. import __short_version__
from ..exceptions import ProviderError
from ..subtitle import (Subtitle, fix_line_ending, guess_matches)
from ..score import get_equivalent_release_groups
from ..utils import sanitize, sanitize_release_group
from ..video import Episode
from guessit import guessit

logger = logging.getLogger(__name__)


class ArgenteamSubtitle(Subtitle):
    provider_name = 'argenteam'

    def __init__(self, language, download_link, series, season, episode, release, version, *args, **kwargs):
        super(ArgenteamSubtitle, self).__init__(language, download_link)
        self.download_link = download_link
        self.series = series
        self.season = season
        self.episode = episode
        self.release = release
        self.version = version

    @property
    def id(self):
        return self.download_link

    def get_matches(self, video):
        matches = set()
        # series
        if video.series and (sanitize(self.series) in (
                 sanitize(name) for name in [video.series] + video.alternative_series)):
            matches.add('series')
        # season
        if video.season and self.season == video.season:
            matches.add('season')
        # episode
        if video.episode and self.episode == video.episode:
            matches.add('episode')

        # release_group
        if (video.release_group and self.version):
            rg = sanitize_release_group(video.release_group)
            if any(r in sanitize_release_group(self.version) for r in get_equivalent_release_groups(rg)):
                matches.add('release_group')

        # resolution
        if video.resolution and self.version and video.resolution in self.version.lower():
            matches.add('resolution')
        # format
        if video.format and self.version and video.format.lower() in self.version.lower():
            matches.add('format')
        matches |= guess_matches(video, guessit(self.version), partial=True)
        return matches


class ArgenteamProvider(Provider):
    provider_name = 'argenteam'
    languages = {Language.fromalpha2(l) for l in ['es']}
    video_types = (Episode,)
    API_URL = "http://argenteam.net/api/v1/"

    def initialize(self):
        self.session = Session()
        self.session.headers = {'User-Agent': 'Subliminal/%s' % __short_version__}

    def terminate(self):
        self.session.close()

    def search_episode_id(self, series, season, episode):
        """Search the episode id from the `series`, `season` and `episode`.

        :param str series: series of the episode.
        :param int season: season of the episode.
        :param int episode: episode number.
        :return: the episode id, if any.
        :rtype: int or None

        """
        # make the search
        query = '%s S%#02dE%#02d' % (series, season, episode)
        logger.info('Searching episode id for %r', query)
        r = self.session.get(self.API_URL + 'search', params={'q': query}, timeout=10)
        r.raise_for_status()
        results = json.loads(r.text)
        episode_id = None
        if results['total'] == 1:
            episode_id = results['results'][0]['id']
        else:
            logger.error('No episode id found for %r', series)

        return episode_id

    def query(self, series, season, episode):

        episode_id = self.search_episode_id(series, season, episode)
        if episode_id is None:
            return []

        response = self.session.get(self.API_URL + 'episode', params={'id': episode_id}, timeout=10)
        response.raise_for_status()
        content = json.loads(response.text)
        language = Language.fromalpha2('es')
        subtitles = []
        for r in content['releases']:
            for s in r['subtitles']:
                sub = ArgenteamSubtitle(language, s['uri'], series, season, episode, r['team'], r['tags'])
                subtitles.append(sub)

        return subtitles

    def list_subtitles(self, video, languages):
        titles = [video.series] + video.alternative_series
        for title in titles:
            subs = self.query(title, video.season, video.episode)
            if subs:
                return subs

        return []

    def download_subtitle(self, subtitle):
        # download as a zip
        r = self.session.get(subtitle.download_link, timeout=10)
        r.raise_for_status()

        # open the zip
        with ZipFile(io.BytesIO(r.content)) as zf:
            if len(zf.namelist()) > 1:
                raise ProviderError('More than one file to unzip')

            subtitle.content = fix_line_ending(zf.read(zf.namelist()[0]))
