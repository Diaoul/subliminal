"""Provider for Subtis."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any, ClassVar
from urllib.parse import quote

from babelfish import Language  # type: ignore[import-untyped]
from guessit import guessit  # type: ignore[import-untyped]
from requests import Session
from requests.exceptions import HTTPError, JSONDecodeError, RequestException

from subliminal.exceptions import NotInitializedProviderError, ProviderError
from subliminal.matches import guess_matches
from subliminal.subtitle import Subtitle
from subliminal.video import Movie

from . import Provider

if TYPE_CHECKING:
    from collections.abc import Set

    from subliminal.video import Video

logger = logging.getLogger(__name__)

subtis_languages: set[Language] = {
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
} | {Language('spa')}


class SubtisSubtitle(Subtitle):
    """Subtis Subtitle."""

    provider_name: ClassVar[str] = 'subtis'

    def __init__(
        self,
        language: Language,
        subtitle_id: str = '',
        *,
        page_link: str | None = None,
        title: str | None = None,
        download_link: str | None = None,
        is_synced: bool = True,
    ) -> None:
        super().__init__(
            language=language,
            subtitle_id=subtitle_id,
            hearing_impaired=False,
            page_link=page_link,
        )
        self.title = title
        self.download_link = download_link
        self.is_synced = is_synced

    @property
    def info(self) -> str:
        """Information about the subtitle."""
        if not self.title:
            return self.id
        sync_indicator = '' if self.is_synced else ' [fuzzy match]'
        return f'{self.title}{sync_indicator}'

    def get_matches(self, video: Video) -> set[str]:
        """Get the matches against the `video`."""
        matches: set[str] = set()

        if not isinstance(video, Movie):
            return matches

        if self.is_synced and video.name:
            # Synced means exact file match - use video filename for full release-level matching
            matches |= guess_matches(video, guessit(os.path.basename(video.name), {'type': 'movie'}))
        elif self.title:
            # Non-synced (fuzzy match) - use subtitle title for basic matching
            matches |= guess_matches(video, guessit(self.title, {'type': 'movie'}))

        return matches


class SubtisProvider(Provider[SubtisSubtitle]):
    """Subtis Provider.

    Provides Spanish subtitles for movies from the subt.is API.
    """

    languages: ClassVar[Set[Language]] = subtis_languages
    video_types: ClassVar = (Movie,)
    subtitle_class: ClassVar = SubtisSubtitle

    server_url: ClassVar[str] = 'https://api.subt.is/v1'

    timeout: int
    session: Session | None

    def __init__(self, *, timeout: int = 10) -> None:
        self.timeout = timeout
        self.session = None

    def initialize(self) -> None:
        """Initialize the provider."""
        self.session = Session()
        self.session.headers['User-Agent'] = self.user_agent
        self.session.headers['Accept'] = 'application/json'

    def terminate(self) -> None:
        """Terminate the provider."""
        if self.session is None:
            raise NotInitializedProviderError
        self.session.close()
        self.session = None

    def _session_request(self, url: str) -> dict[str, Any] | None:
        """Perform a GET request to the provider."""
        if self.session is None:
            raise NotInitializedProviderError

        try:
            r = self.session.get(url, timeout=self.timeout)
        except RequestException:
            logger.exception('Request error for %s', url)
            raise SubtisError from None

        if r.status_code in (400, 404):
            return None

        try:
            r.raise_for_status()
        except HTTPError:
            msg = f'Unexpected status {r.status_code}'
            logger.warning('%s for %s', msg, url)
            raise SubtisError(msg) from None

        try:
            return r.json()  # type: ignore[no-any-return]
        except JSONDecodeError:
            msg = 'Invalid JSON response'
            logger.exception('%s for %s', msg, url)
            raise SubtisError(msg) from None

    def _parse_response(self, data: dict[str, Any]) -> tuple[str, str] | None:
        """Parse API response and extract subtitle link and title.

        Returns:
            Tuple of (subtitle_link, title_name), or None if required fields are missing.
        """
        subtitle_data = data.get('subtitle')
        if not isinstance(subtitle_data, dict):
            return None

        subtitle_link = subtitle_data.get('subtitle_link')
        if not isinstance(subtitle_link, str) or not subtitle_link:
            return None

        title_data = data.get('title', {})
        title_name = title_data.get('title_name', 'Unknown') if isinstance(title_data, dict) else 'Unknown'

        return subtitle_link, str(title_name)

    def query(self, video: Movie, languages: Set[Language]) -> list[SubtisSubtitle]:
        """Query the provider for subtitles."""
        if not video.name:
            return []

        # Find a Spanish language from the requested languages
        language = next((lang for lang in languages if lang.alpha3 == 'spa'), Language('spa'))

        filename = os.path.basename(video.name)
        encoded_filename = quote(filename, safe='')

        # Try primary search (exact match by size + filename)
        if video.size:
            primary_url = f'{self.server_url}/subtitle/file/name/{video.size}/{encoded_filename}'
            logger.info('Searching subtitles (primary) for %s', filename)
            data = self._session_request(primary_url)
            if data:
                parsed = self._parse_response(data)
                if parsed:
                    subtitle_link, title_name = parsed
                    logger.debug('Found subtitle via primary search')
                    return [
                        SubtisSubtitle(
                            language=language,
                            subtitle_id=subtitle_link,
                            page_link=primary_url,
                            title=title_name,
                            download_link=subtitle_link,
                            is_synced=True,
                        )
                    ]

        # Fallback to alternative search (fuzzy match by filename only)
        alternative_url = f'{self.server_url}/subtitle/file/alternative/{encoded_filename}'
        logger.info('Searching subtitles (alternative) for %s', filename)
        data = self._session_request(alternative_url)
        if data:
            parsed = self._parse_response(data)
            if parsed:
                subtitle_link, title_name = parsed
                logger.debug('Found subtitle via alternative search (fuzzy)')
                return [
                    SubtisSubtitle(
                        language=language,
                        subtitle_id=subtitle_link,
                        page_link=alternative_url,
                        title=title_name,
                        download_link=subtitle_link,
                        is_synced=False,
                    )
                ]

        logger.info('No subtitle found for %s', filename)
        return []

    def list_subtitles(self, video: Video, languages: Set[Language]) -> list[SubtisSubtitle]:
        """List all the subtitles for the video."""
        if not isinstance(video, Movie):
            return []

        return self.query(video, languages)

    def download_subtitle(self, subtitle: SubtisSubtitle) -> None:
        """Download the content of the subtitle."""
        if self.session is None:
            raise NotInitializedProviderError

        if not subtitle.download_link:
            return

        logger.info('Downloading subtitle %s', subtitle.download_link)

        try:
            r = self.session.get(subtitle.download_link, timeout=self.timeout)
            r.raise_for_status()
        except RequestException:
            logger.exception('Download error for %s', subtitle.download_link)
            raise SubtisError from None

        if not r.content:
            logger.warning('Empty subtitle content from %s', subtitle.download_link)
            return

        subtitle.set_content(r.content)


class SubtisError(ProviderError):
    """Base class for non-generic :class:`SubtisProvider` exceptions."""
