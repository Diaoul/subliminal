"""Provider for Gestdown."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any, ClassVar

from babelfish import Language  # type: ignore[import-untyped]
from guessit import guessit  # type: ignore[import-untyped]
from requests import HTTPError, Session

from subliminal.exceptions import DownloadLimitExceeded, NotInitializedProviderError
from subliminal.matches import guess_matches
from subliminal.subtitle import Subtitle, fix_line_ending
from subliminal.utils import sanitize
from subliminal.video import Episode, Video

from . import Provider

if TYPE_CHECKING:
    from collections.abc import Set

logger = logging.getLogger(__name__)

#: Subtitle id pattern
id_pattern = re.compile(r'.*\/subtitles\/download\/([a-z0-9-]+)')

gestdown_languages: Set[Language] = {
    Language(lang)
    for lang in [
        'ara',
        'aze',
        'ben',
        'bos',
        'bul',
        'cat',
        'ces',
        'dan',
        'deu',
        'ell',
        'eng',
        'eus',
        'fas',
        'fin',
        'fra',
        'glg',
        'heb',
        'hrv',
        'hun',
        'hye',
        'ind',
        'ita',
        'jpn',
        'kor',
        'mkd',
        'msa',
        'nld',
        'nor',
        'pol',
        'por',
        'ron',
        'rus',
        'slk',
        'slv',
        'spa',
        'sqi',
        'srp',
        'swe',
        'tha',
        'tur',
        'ukr',
        'vie',
        'zho',
    ]
}


class GestdownSubtitle(Subtitle):
    """Gestdown Subtitle."""

    provider_name: ClassVar[str] = 'gestdown'

    series: str
    season: int | None
    episode: int | None
    title: str | None
    release_group: str | None

    def __init__(
        self,
        language: Language,
        subtitle_id: str,
        *,
        hearing_impaired: bool = False,
        page_link: str | None = None,
        series: str = '',
        season: int | None = None,
        episode: int | None = None,
        title: str | None = None,
        release_group: str = '',
    ) -> None:
        super().__init__(language, subtitle_id, hearing_impaired=hearing_impaired, page_link=page_link)
        self.series = series
        self.season = season
        self.episode = episode
        self.title = title
        self.release_group = release_group

    @property
    def info(self) -> str:
        """Information about the subtitle."""
        parts = []
        if self.title:
            parts.append(self.title)
        if self.release_group:
            parts.append(self.release_group)
        title_part = ' - '.join(parts)
        return f'{self.series} s{self.season:02d}e{self.episode:02d}{title_part}'

    def get_matches(self, video: Video) -> set[str]:
        """Get the matches against the `video`."""
        # series name
        matches = guess_matches(
            video,
            {
                'title': self.series,
                'season': self.season,
                'episode': self.episode,
                'episode_title': self.title,
                'release_group': self.release_group,
            },
        )

        # resolution
        if self.release_group and video.resolution and video.resolution in self.release_group.lower():
            matches.add('resolution')

        # other properties
        if self.release_group:
            matches |= guess_matches(
                video,
                guessit(self.release_group, {'type': 'episode'}),
                partial=True,
            )

        return matches


class GestdownProvider(Provider):
    """Gestdown Provider."""

    languages: ClassVar[Set[Language]] = gestdown_languages
    video_types: ClassVar = (Episode,)
    server_url: ClassVar[str] = 'https://api.gestdown.info'
    subtitle_class: ClassVar = GestdownSubtitle

    timeout: int
    session: Session | None

    def __init__(self, *, timeout: int = 10) -> None:
        self.timeout = timeout
        self.session = None

    def initialize(self) -> None:
        """Initialize the provider."""
        self.session = Session()
        self.session.headers['User-Agent'] = self.user_agent
        self.session.headers['accept'] = 'application/json'

    def terminate(self) -> None:
        """Terminate the provider."""
        if self.session is None:
            raise NotInitializedProviderError

        self.session.close()

    def _search_show_id(self, series: str, series_tvdb_id: str | None = None) -> str | None:
        """Search the show id from the `series`.

        :param str series: series of the episode.
        :param str series_tvdb_id: tvdb id of the series.
        :return: the show id, if found.
        :rtype: str

        """
        if self.session is None:
            raise NotInitializedProviderError

        # build the params
        if series_tvdb_id is not None:
            query = f'{self.server_url}/shows/external/tvdb/{series_tvdb_id}'
            logger.info('Searching show ids for TVBD id %s', series_tvdb_id)
        else:
            query = f'{self.server_url}/shows/search/{series}'
            logger.info('Searching show ids for %s', series)

        # make the search
        r = self.session.get(query, timeout=self.timeout)
        try:
            r.raise_for_status()
        except HTTPError:
            logger.warning('Show id not found: no suggestion')
            return None

        result = r.json()

        # get the suggestion
        for show in result['shows']:
            if not series or sanitize(show['name']) == sanitize(series):
                show_id = str(show['id'])
                logger.debug('Found show id %s', show_id)
                return show_id

        logger.warning('Show id not found: suggestion does not match: %r', result)
        return None

    def get_title_and_show_id(self, video: Episode) -> tuple[str, str | None]:
        """Get the title and show_id."""
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

    def _query_all_episodes(self, show_id: str, season: int, language: Language) -> list[dict[str, Any]]:
        """Get the subtitles in the specified language for all the episodes of a season of the show.

        :param str show_id: the show id.
        :param int season: the season to query.
        :param language: the language of the subtitles.
        :type language: :class:`~babelfish.language.Language`
        :return: the list of found subtitles (as dicts).
        :rtype: list[dict[str, Any]]
        """
        if self.session is None:
            raise NotInitializedProviderError

        query = f'{self.server_url}/shows/{show_id}/{season}/{language.alpha3}'
        r = self.session.get(query, timeout=self.timeout)
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

        return result['episodes']  # type: ignore[no-any-return]

    def _query_single_episode(
        self,
        show_id: str,
        season: int,
        episode: int,
        language: Language,
    ) -> list[dict[str, Any]]:
        """Get the subtitles in the specified language of a single episode (and season) of the show.

        :param str show_id: the show id.
        :param int season: the season to query.
        :param int episode: the episode to query.
        :param language: the language of the subtitles.
        :type language: :class:`~babelfish.language.Language`
        :return: the list of found subtitles (as dicts).
        :rtype: list[dict[str, Any]]
        """
        if self.session is None:
            raise NotInitializedProviderError

        base_query = f'{self.server_url}/subtitles/get'
        query = f'{base_query}/{show_id}/{season}/{episode}/{language.alpha3}'

        r = self.session.get(query, timeout=self.timeout)
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
        data: dict[str, Any] = result['episode']
        data['subtitles'] = result['matchingSubtitles']
        return [data]

    def query(
        self,
        show_id: str | None,
        series: str,
        season: int,
        episode: int | None,
        language: Language,
    ) -> list[GestdownSubtitle]:
        """Query the provider for subtitles.

        :param (str | None) show_id: the show id.
        :param str series: the series title.
        :param int season: the season number.
        :param int episode: the episode number.
        :param language: the language of the subtitles.
        :type language: :class:`~babelfish.language.Language`
        :return: the list of found subtitles.
        :rtype: list[GestdownSubtitle]

        """
        # get the page of the season of the show
        if show_id is None:
            logger.debug('A show id must be provided, show_id=None is not allowed')
            return []

        logger.info('Getting the subtitles list of show id %s, season %d', show_id, season)
        if language is None:
            logger.debug('A language for the subtitle must be provided, language=None is not allowed')
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
                page_link = f"{self.server_url}{subtitle['downloadUri']}"
                release_group = subtitle['version']

                m = id_pattern.match(page_link)
                subtitle_id = m.groups()[0] if m else page_link

                subtitle = self.subtitle_class(
                    language=language,
                    subtitle_id=subtitle_id,
                    hearing_impaired=hearing_impaired,
                    series=series,
                    season=season,
                    episode=episode,
                    title=title,
                    release_group=release_group,
                    page_link=page_link,
                )
                logger.debug('Found subtitle %r', subtitle)
                subtitles.append(subtitle)

        return subtitles

    def list_subtitles(self, video: Video, languages: Set[Language]) -> list[GestdownSubtitle]:
        """List all the subtitles for the video."""
        if not isinstance(video, Episode):
            return []

        # lookup title and show_id
        title, show_id = self.get_title_and_show_id(video)

        # Cannot find show_id
        if show_id is None:
            logger.error('No show id found for %r', video.series)
            return []

        # query for subtitles with the show_id
        subtitles = []
        for lang in languages:
            subtitles.extend(self.query(show_id, title, video.season, video.episode, lang))

        return subtitles

    def download_subtitle(self, subtitle: GestdownSubtitle) -> None:
        """Download the content of the subtitle."""
        if self.session is None:
            raise NotInitializedProviderError

        if not subtitle.page_link:
            return

        # download the subtitle
        logger.info('Downloading subtitle %r', subtitle)
        r = self.session.get(subtitle.page_link, timeout=self.timeout)
        try:
            r.raise_for_status()
        except HTTPError:
            logger.exception('Could not download subtitle %s', subtitle)
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
