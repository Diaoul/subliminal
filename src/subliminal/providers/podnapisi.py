"""Provider for Podnapisi."""

from __future__ import annotations

import io
import json
import logging
from typing import TYPE_CHECKING, Any, ClassVar
from zipfile import ZipFile

from babelfish import Language, language_converters  # type: ignore[import-untyped]
from guessit import guessit  # type: ignore[import-untyped]
from requests import Session

from subliminal.exceptions import NotInitializedProviderError, ProviderError
from subliminal.matches import guess_matches
from subliminal.subtitle import Subtitle, fix_line_ending
from subliminal.video import Episode, Movie, Video

from . import Provider, SecLevelOneTLSAdapter

if TYPE_CHECKING:
    from collections.abc import Sequence, Set


logger = logging.getLogger(__name__)


class PodnapisiSubtitle(Subtitle):
    """Podnapisi Subtitle."""

    provider_name: ClassVar[str] = 'podnapisi'

    subtitle_id: str
    releases: Sequence[str]
    title: str | None
    season: int | None
    episode: int | None
    year: int | None

    def __init__(
        self,
        language: Language,
        subtitle_id: str,
        *,
        hearing_impaired: bool = False,
        page_link: str | None = None,
        releases: Sequence[str] | None = None,
        title: str | None = None,
        season: int | None = None,
        episode: int | None = None,
        year: int | None = None,
    ) -> None:
        super().__init__(language, subtitle_id, hearing_impaired=hearing_impaired, page_link=page_link)
        self.releases = list(releases) if releases is not None else []
        self.title = title
        self.season = season
        self.episode = episode
        self.year = year

    @property
    def info(self) -> str:
        """Information about the subtitle."""
        return ' '.join(self.releases) if self.releases else self.id

    def get_matches(self, video: Video) -> set[str]:
        """Get the matches against the `video`."""
        matches = guess_matches(
            video,
            {
                'title': self.title,
                'year': self.year,
                'season': self.season,
                'episode': self.episode,
            },
        )

        video_type = 'episode' if isinstance(video, Episode) else 'movie'
        for release in self.releases:
            matches |= guess_matches(video, guessit(release, {'type': video_type}))

        return matches


class PodnapisiProvider(Provider):
    """Podnapisi Provider."""

    languages: ClassVar[Set[Language]] = {Language('por', 'BR'), Language('srp', script='Latn')} | {
        Language.fromalpha2(lang) for lang in language_converters['alpha2'].codes
    }
    subtitle_class: ClassVar = PodnapisiSubtitle
    server_url: ClassVar[str] = 'https://www.podnapisi.net/subtitles'

    timeout: int
    session: Session | None

    def __init__(self, *, timeout: int = 10) -> None:
        self.timeout = timeout
        self.session = None

    def initialize(self) -> None:
        """Initialize the provider."""
        self.session = Session()
        self.session.mount('https://', SecLevelOneTLSAdapter())
        self.session.headers['User-Agent'] = self.user_agent
        self.session.headers['Accept'] = 'application/json'

    def terminate(self) -> None:
        """Terminate the provider."""
        if self.session is None:
            raise NotInitializedProviderError

        self.session.close()

    def query(
        self,
        language: Language,
        keyword: str,
        *,
        season: int | None = None,
        episode: int | None = None,
        year: int | None = None,
    ) -> list[PodnapisiSubtitle]:
        """Query the provider for subtitles.

        :param :class:`~babelfish.language.Language` language: the language of the subtitles.
        :param str keyword: the query term.
        :param (int | None) season: the season number.
        :param (int | None) episode: the episode number.
        :param (int | None) year: the video year.
        :return: the list of found subtitles.
        :rtype: list[PodnapisiSubtitle]

        """
        if self.session is None:
            raise NotInitializedProviderError

        # set parameters, see https://www.podnapisi.net/forum/viewtopic.php?f=62&t=26164#p212652
        params: dict[str, Any] = {'keywords': keyword, 'language': str(language)}
        is_episode = False
        if season is not None and episode is not None:
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
            r = self.session.get(self.server_url + '/search/advanced', params=params, timeout=self.timeout)
            r.raise_for_status()
            result = json.loads(r.text)

            # loop over subtitles
            for data in result['data']:
                # read xml elements
                pid = data['id']
                # ignore duplicates, see https://www.podnapisi.net/forum/viewtopic.php?f=62&t=26164&start=10#p213321
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

                subtitle = self.subtitle_class(
                    language=language,
                    subtitle_id=pid,
                    hearing_impaired=hearing_impaired,
                    page_link=page_link,
                    releases=releases,
                    title=title,
                    season=season,
                    episode=episode,
                    year=year,
                )

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

    def list_subtitles(self, video: Video, languages: Set[Language]) -> list[PodnapisiSubtitle]:
        """List all the subtitles for the video."""
        season = episode = None
        if isinstance(video, Episode):
            titles = [video.series, *video.alternative_series]
            season = video.season
            episode = video.episode
        elif isinstance(video, Movie):
            titles = [video.title, *video.alternative_titles]
        else:
            return []

        for title in titles:
            subtitles = [
                s
                for lang in languages
                for s in self.query(lang, title, season=season, episode=episode, year=video.year)
            ]
            if subtitles:
                return subtitles

        return []

    def download_subtitle(self, subtitle: PodnapisiSubtitle) -> None:
        """Download the content of the subtitle."""
        if self.session is None:
            raise NotInitializedProviderError

        # download as a zip
        logger.info('Downloading subtitle %r', subtitle)
        r = self.session.get(
            self.server_url + f'/{subtitle.subtitle_id}/download',
            params={'container': 'zip'},
            timeout=self.timeout,
        )
        r.raise_for_status()

        # open the zip
        with ZipFile(io.BytesIO(r.content)) as zf:
            if len(zf.namelist()) > 1:
                msg = 'More than one file to unzip'
                raise ProviderError(msg)

            subtitle.content = fix_line_ending(zf.read(zf.namelist()[0]))
