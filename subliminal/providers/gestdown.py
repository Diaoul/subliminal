# -*- coding: utf-8 -*-
import logging
import re

from babelfish import Language
from guessit import guessit
from requests import HTTPError, Session

from . import Provider
from ..exceptions import DownloadLimitExceeded
from ..matches import guess_matches
from ..subtitle import Subtitle, fix_line_ending
from ..utils import sanitize
from ..video import Episode

logger = logging.getLogger(__name__)


class GestdownSubtitle(Subtitle):
    """Gestdown Subtitle."""
    provider_name = 'gestdown'
    id_pattern = r'.*\/subtitles\/download\/([a-z0-9-]+)'

    def __init__(
        self, language, hearing_impaired, series, season, episode, title, version,
        download_link,
    ):
        super(GestdownSubtitle, self).__init__(language, hearing_impaired=hearing_impaired)
        self.series = series
        self.season = season
        self.episode = episode
        self.title = title
        self.version = version
        self.download_link = download_link

        subtitle_id = None
        if download_link:
            m = re.match(self.id_pattern, download_link)
            if m:
                subtitle_id = m.groups()[0]
        self.subtitle_id = subtitle_id or download_link

    @property
    def id(self):
        return self.subtitle_id

    @property
    def info(self):
        title = ' - {} - '.format(self.title) if self.title else ' - '
        return '{series} s{season:02d}e{episode:02d}{title}{version}'.format(
            series=self.series,
            season=self.season,
            episode=self.episode,
            title=title,
            version=self.version,
        )

    def get_matches(self, video):
        # series name
        matches = guess_matches(video, {
            'title': self.series,
            'season': self.season,
            'episode': self.episode,
            'episode_title': self.title,
            'release_group': self.version,
        })

        # resolution
        if self.version and video.resolution and video.resolution in self.version.lower():
            matches.add('resolution')
        # other properties
        if self.version:
            matches |= guess_matches(
                video,
                guessit(self.version, {'type': 'episode'}),
                partial=True,
            )

        return matches


class GestdownProvider(Provider):
    """Gestdown Provider."""
    languages = {Language(lang) for lang in [
        'ara', 'aze', 'ben', 'bos', 'bul', 'cat', 'ces', 'dan', 'deu', 'ell', 'eng',
        'eus', 'fas', 'fin', 'fra', 'glg', 'heb', 'hrv', 'hun', 'hye', 'ind', 'ita',
        'jpn', 'kor', 'mkd', 'msa', 'nld', 'nor', 'pol', 'por', 'ron', 'rus', 'slk',
        'slv', 'spa', 'sqi', 'srp', 'swe', 'tha', 'tur', 'ukr', 'vie', 'zho',
    ]}
    video_types = (Episode,)
    server_url = 'https://api.gestdown.info'
    subtitle_class = GestdownSubtitle

    def __init__(self):
        self.session = None

    def initialize(self):
        self.session = Session()
        self.session.headers['User-Agent'] = self.user_agent
        self.session.headers['accept'] = 'application/json'

    def terminate(self):
        if self.session is None:
            return
        self.session.close()

    def _search_show_id(self, series, series_tvdb_id=None):
        """Search the show id from the `series`.

        :param str series: series of the episode.
        :param int series_tvdb_id: tvdb id of the series.
        :return: the show id, if found.
        :rtype: int

        """
        if self.session is None:
            return
        # build the params
        if series_tvdb_id is not None:
            query = f"{self.server_url}/shows/external/tvdb/{series_tvdb_id}"
            logger.info(f'Searching show ids for TVBD id {series_tvdb_id}')
        else:
            query = f"{self.server_url}/shows/search/{series}"
            logger.info(f'Searching show ids for {series}')

        # make the search
        r = self.session.get(query, timeout=10)
        try:
            r.raise_for_status()
        except HTTPError:
            logger.warning('Show id not found: no suggestion')
            return None

        result = r.json()

        # get the suggestion
        for show in result['shows']:
            if not series or sanitize(show['name']) == sanitize(series):
                show_id = show['id']
                logger.debug(f'Found show id {show_id}')
                return show_id

        logger.warning('Show id not found: suggestion does not match: %r', result)
        return None

    def get_title_and_show_id(self, video):
        # lookup show_id
        series_tvdb_id = getattr(video, 'series_tvdb_id', None)
        title = video.series
        show_id = self._search_show_id(title, series_tvdb_id=series_tvdb_id)

        # Try alternative names
        if show_id is None:
            for title in video.alternative_series:
                show_id = self._search_show_id(title)
                if show_id is not None:
                    # show_id found, keep the title and show_id
                    break

        return (title, show_id)

    def _query_all_episodes(self, show_id, season, language):
        if self.session is None:
            return
        query = f"{self.server_url}/shows/{show_id}/{season}/{language.alpha3}"
        r = self.session.get(query, timeout=10)
        try:
            r.raise_for_status()
        except HTTPError:
            logger.exception('wrong query: %s', query)
            return []

        result = r.json()
        if not result or 'episodes' not in result:
            # Provider returns a status of 304 Not Modified with an empty content
            # raise_for_status won't raise exception for that status code
            logger.debug('No data returned from provider')
            return []

        return result["episodes"]

    def _query_single_episode(self, show_id, season, episode, language):
        if self.session is None:
            return
        base_query = f"{self.server_url}/subtitles/get"
        query = f"{base_query}/{show_id}/{season}/{episode}/{language.alpha3}"

        r = self.session.get(query, timeout=10)
        try:
            r.raise_for_status()
        except HTTPError:
            logger.exception('wrong query: %s', query)
            return []

        result = r.json()
        if not result or any(k not in result for k in ('episode', 'matchingSubtitles')):
            # Provider returns a status of 304 Not Modified with an empty content
            # raise_for_status won't raise exception for that status code
            logger.debug('No data returned from provider')
            return []

        # Transform to list of episodes, identical to `query_all_episodes`
        episode = result["episode"]
        episode['subtitles'] = result['matchingSubtitles']
        return [episode]

    def query(self, show_id, series, season, episode, language):
        # get the page of the season of the show
        logger.info(
            'Getting the subtitles list of show id %d, season %d', show_id, season
        )
        if language is None:
            logger.debug(
                'A language for the subtitle must be provided, language=None is not allowed'
            )
            return []


        if episode is None:
            # download for the given season of the show
            episodes = self._query_all_episodes(show_id, season, language)

        else:
            # download only the specified episode
            episodes = self._query_single_episode(show_id, season, episode, language)

        # loop over subtitle rows
        subtitles = []
        for found in episodes:
            title = found['title']
            episode = found['number']
            season = found['season']
            for subtitle in found['subtitles']:
                # read the item
                hearing_impaired = subtitle['hearingImpaired']
                download_link = f"{self.server_url}{subtitle['downloadUri']}"
                version = subtitle['version']

                subtitle = self.subtitle_class(
                    language,
                    hearing_impaired,
                    series,
                    season,
                    episode,
                    title,
                    version,
                    download_link,
                )
                logger.debug('Found subtitle %r', subtitle)
                subtitles.append(subtitle)

        return subtitles

    def list_subtitles(self, video, languages):
        # lookup title and show_id
        title, show_id = self.get_title_and_show_id(video)

        # Cannot find show_id
        if show_id is None:
            logger.error('No show id found for %r', video.series)
            return []

        # query for subtitles with the show_id
        subtitles = []
        for lang in languages:
            subtitles.extend(
                self.query(show_id, title, video.season, video.episode, lang)
            )

        return subtitles

    def download_subtitle(self, subtitle):
        if self.session is None:
            return
        # download the subtitle
        logger.info('Downloading subtitle %r', subtitle)
        r = self.session.get(
            subtitle.download_link,
            headers={'Referer': subtitle.page_link},
            timeout=10,
        )
        try:
            r.raise_for_status()
        except HTTPError:
            logger.exception("Could not download subtitle %s", subtitle)
            return

        if not r.content:
            # Provider returns a status of 304 Not Modified with an empty content
            # raise_for_status won't raise exception for that status code
            logger.debug('Unable to download subtitle. No data returned from provider')
            return

        # detect download limit exceeded
        if r.headers['Content-Type'] == 'text/html':
            raise DownloadLimitExceeded

        subtitle.content = fix_line_ending(r.content)
