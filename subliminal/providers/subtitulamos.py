"""Provider for Subtitulamos."""

from __future__ import annotations

import contextlib
import json
import logging
from typing import TYPE_CHECKING, Any, ClassVar, cast

from babelfish import Language, language_converters  # type: ignore[import-untyped]
from bs4 import Tag
from guessit import guessit  # type: ignore[import-untyped]
from requests import Session

from subliminal import __short_version__
from subliminal.cache import SHOW_EXPIRATION_TIME, region
from subliminal.exceptions import NotInitializedProviderError, ProviderError
from subliminal.matches import guess_matches
from subliminal.subtitle import Subtitle, fix_line_ending
from subliminal.video import Episode

from . import ParserBeautifulSoup, Provider

if TYPE_CHECKING:
    from collections.abc import Set

    from requests import Response

    from subliminal.video import Video

logger = logging.getLogger(__name__)

with contextlib.suppress(ValueError):
    language_converters.register('subtitulamos = subliminal.converters.subtitulamos:SubtitulamosConverter')


subtitulamos_languages = (
    {Language('por', 'BR')}
    | {
        Language('spa', country)
        for country in [
            'AR',  # Argentina
            'BO',  # Bolivia
            'CL',  # Chile
            'CO',  # Colombia
            'CR',  # Costa Rica
            'DO',  # República Dominicana
            'EC',  # Ecuador
            'GT',  # Guatemala
            'HN',  # Honduras
            'MX',  # México
            'NI',  # Nicaragua
            'PA',  # Panamá
            'PE',  # Perú
            'PR',  # Puerto Rico
            'PY',  # Paraguay
            'SV',  # El Salvador
            'US',  # United States
            'UY',  # Uruguay
            'VE',  # Venezuela
        ]
    }
    | {Language(lang) for lang in ['cat', 'eng', 'glg', 'por', 'spa']}
)


class SubtitulamosSubtitle(Subtitle):
    """Subtitulamos Subtitle."""

    provider_name: ClassVar[str] = 'subtitulamos'

    def __init__(
        self,
        language: Language,
        subtitle_id: str = '',
        hearing_impaired: bool | None = None,
        page_link: str | None = None,
        series: str | None = None,
        season: int | None = None,
        episode: int | None = None,
        title: str | None = None,
        year: int | None = None,
        release_group: str | None = None,
        download_link: str | None = None,
    ) -> None:
        super().__init__(
            language=language,
            subtitle_id=subtitle_id,
            hearing_impaired=hearing_impaired,
            page_link=page_link,
        )
        self.series = series
        self.season = season
        self.episode = episode
        self.title = title
        self.year = year
        self.release_group = release_group
        self.download_link = download_link

    def get_matches(self, video: Video) -> set[str]:
        """Get the matches against the `video`."""
        matches = guess_matches(
            video,
            {
                'title': self.series,
                'season': self.season,
                'episode': self.episode,
                'episode_title': self.title,
                'year': self.year,
                'release_group': self.release_group,
            },
        )

        # other properties
        matches |= guess_matches(video, guessit(self.release_group), partial=True)

        return matches


class SubtitulamosProvider(Provider):
    """Subtitulamos Provider."""

    languages: ClassVar[Set[Language]] = subtitulamos_languages
    video_types: ClassVar = (Episode,)

    server_url = 'https://www.subtitulamos.tv'
    search_url = server_url + '/search/query'

    timeout: int
    session: Session | None

    def __init__(self, *, timeout: int = 10) -> None:
        self.session = None
        self.timeout = timeout

    def initialize(self) -> None:
        """Initialize the provider."""
        self.session = Session()
        self.session.headers['User-Agent'] = f'Subliminal/{__short_version__}'

    def terminate(self) -> None:
        """Terminate the provider."""
        if not self.session:
            raise NotInitializedProviderError
        self.session.close()
        self.session = None

    def _session_request(self, *args: Any, **kwargs: Any) -> Response:
        """Perform a GET request to the provider."""
        if not self.session:
            raise NotInitializedProviderError

        r = self.session.get(*args, **kwargs)
        r.raise_for_status()

        if r.status_code != 200:
            msg = 'Error requesting data'
            raise ProviderError(msg)

        return r

    def _query_search(self, search_param: str) -> list[dict[str, str]]:
        """Search Series/Series + Season using query search method."""
        r = self._session_request(
            self.search_url,
            headers={'Referer': self.server_url},
            params={'q': search_param},
            timeout=self.timeout,
        )
        data = json.loads(r.text)
        return cast(list[dict[str, str]], data)

    def _read_series(self, series_url: str) -> ParserBeautifulSoup:
        """Read series information from provider."""
        r = self._session_request(
            self.server_url + series_url,
            headers={'Referer': self.server_url},
            timeout=self.timeout,
        )
        return ParserBeautifulSoup(r.content, ['lxml', 'html.parser'])

    @region.cache_on_arguments(expiration_time=SHOW_EXPIRATION_TIME)
    def _read_episode_page(
        self, series: str, season: int, episode: int, year: int | None = None
    ) -> tuple[ParserBeautifulSoup, str]:
        """Search the URL titles by kind for the given `title`, `season` and `episode`.

        :param str series: Series to search for.
        :param int season: Season to search for.
        :param int episode: Episode to search for.
        :param int year: Year to search for.
        :return: The episode URL.

        """
        logger.info('Searching episode url for %s, season %d, episode %d', series, season, episode)

        # attempt first with year
        series_response = self._query_search(f'{series} ({year})')
        if len(series_response) == 0:
            series_response = self._query_search(series)

        if len(series_response) == 0:
            msg = 'Series not found'
            raise NotExists(msg)

        # Provides the URL for a specific episode of the series
        show_id = series_response[0]['show_id']
        page_content = self._read_series(f'/shows/{show_id}')

        # Select season
        season_element = next(
            (el for el in page_content.select('#season-choices a.choice') if str(season) in el.text), None
        )
        if season_element is None:
            msg = 'Season not found'
            raise NotExists(msg)

        if 'selected' not in cast(list[str], season_element.get('class', [])):
            page_content = self._read_series(str(season_element.get('href', '')))

        # Select episode
        episode_element = next(
            (el for el in page_content.select('#episode-choices a.choice') if str(episode) in el.text), None
        )
        if episode_element is None:
            msg = 'Episode not found'
            raise NotExists(msg)

        episode_url = str(episode_element.get('href', ''))
        if 'selected' not in cast(list[str], episode_element.get('class', [])):
            page_content = self._read_series(episode_url)

        return page_content, episode_url

    def _query_provider(
        self, series: str | None = None, season: int | None = None, episode: int | None = None, year: int | None = None
    ) -> list[SubtitulamosSubtitle]:
        """Query the provider for subtitles."""
        # get the episode page content
        soup, episode_url = self._read_episode_page(series, season, episode, year)

        # get episode title
        title = soup.select('#episode-name h3')[0].get_text().strip().lower()

        subtitles = []
        for sub in soup.select('.download-button:not(unavailable)'):
            # read the language
            if (
                sub.parent is None
                or (lang_name_element := sub.find_previous('div', class_='language-name')) is None
                or (version_container := sub.find_previous('div', class_='version-container')) is None
                or not isinstance(version_container, Tag)
                or (release_group_element := version_container.select('.version-container .text.spaced')) is None
            ):
                continue

            language = Language.fromsubtitulamos(lang_name_element.get_text().strip())

            # read the release subtitle
            release_group = release_group_element[0].getText()

            # read the subtitle url
            subtitle_id = str(sub.parent.get('href', ''))
            subtitle_url = self.server_url + subtitle_id
            subtitle = SubtitulamosSubtitle(
                language=language,
                subtitle_id=subtitle_id,
                page_link=self.server_url + episode_url,
                series=series,
                season=season,
                episode=episode,
                title=title,
                year=year,
                release_group=release_group,
                download_link=subtitle_url,
            )
            logger.debug('Found subtitle %r', subtitle)
            subtitles.append(subtitle)

        return subtitles

    def query(
        self,
        series: str | None = None,
        season: int | None = None,
        episode: int | None = None,
        year: int | None = None,
    ) -> list[SubtitulamosSubtitle]:
        """Query the provider for subtitles."""
        try:
            return self._query_provider(series, season, episode, year)
        except NotExists:
            return []

    def list_subtitles(self, video: Video, languages: Set[Language]) -> list[SubtitulamosSubtitle]:
        """List all the subtitles for the video."""
        if not isinstance(video, Episode):
            return []

        result = []
        for subtitle in self.query(video.series, video.season, video.episode, video.year):
            subtitle_lang = next(
                (lang for lang in languages if lang.subtitulamos == subtitle.language.subtitulamos), None
            )
            if subtitle_lang:
                result.append(subtitle)
                # All spanish variations are labeled as "Español (Latinoamérica)",
                # which is guessed as es-MX; this replaces it with the specified one.
                subtitle.language = subtitle_lang

        return result

    def download_subtitle(self, subtitle: SubtitulamosSubtitle) -> None:
        """Download the content of the subtitle."""
        if not self.session:
            raise NotInitializedProviderError

        if not subtitle.download_link:
            return

        logger.info('Downloading subtitle %s', subtitle.download_link)
        r = self.session.get(subtitle.download_link, headers={'Referer': subtitle.page_link}, timeout=10)
        r.raise_for_status()

        subtitle.content = fix_line_ending(r.content)


class SubtitulamosError(ProviderError):
    """Base class for non-generic :class:`SubtitulamosProvider` exceptions."""

    pass


class NotExists(SubtitulamosError):
    """Exception raised when the season and/or the episode does not exist on provider."""

    def __init__(self, msg: str) -> None:
        super().__init__(msg)
        logger.debug(f'Unable to download subtitle. Reason: {msg}')
