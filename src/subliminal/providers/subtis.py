"""Provider for Subtis."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any, ClassVar
from urllib.parse import quote

from babelfish import Language
from guessit import guessit
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
        'AR',
        'BO',
        'CL',
        'CO',
        'CR',
        'DO',
        'EC',
        'GT',
        'HN',
        'MX',
        'NI',
        'PA',
        'PE',
        'PR',
        'PY',
        'SV',
        'US',
        'UY',
        'VE',
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
        video_hash: str | None = None,
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
        self.video_hash = video_hash

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

        if self.video_hash and 'subtis' in video.hashes and self.video_hash == video.hashes['subtis']:
            matches.add('hash')

        if self.is_synced and video.name:
            matches |= guess_matches(video, guessit(os.path.basename(video.name), {'type': 'movie'}))
        elif self.title:
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

    @staticmethod
    def hash_video(video_path: str | os.PathLike) -> str | None:
        """Compute a hash using OpenSubtitles' algorithm.

        :param video_path: path of the video file.
        :return: the hash string, or None if file is too small or error occurs.
        """
        from subliminal.refiners.hash import hash_opensubtitles

        try:
            return hash_opensubtitles(video_path)
        except (OSError, IOError):
            logger.debug('Could not compute hash for %s', video_path)
            return None

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
            return r.json()
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
        """Query the provider for subtitles using cascade search.

        Cascade order (from most to least specific):
        1. Hash - OpenSubtitles video hash (most precise)
        2. Bytes - File size match
        3. Filename - Exact filename match
        4. Alternative - Fuzzy match (fallback)
        """
        if not video.name:
            return []

        language = next((lang for lang in languages if lang.alpha3 == 'spa'), Language('spa'))

        filename = os.path.basename(video.name)
        encoded_filename = quote(filename, safe='')

        if video.name and os.path.isfile(video.name):
            video_hash = video.hashes.get('subtis') or self.hash_video(video.name)
            if video_hash:
                hash_url = f'{self.server_url}/subtitle/find/file/hash/{video_hash}'
                logger.info('Searching subtitles by hash for %s', filename)
                data = self._session_request(hash_url)
                if data:
                    parsed = self._parse_response(data)
                    if parsed:
                        subtitle_link, title_name = parsed
                        logger.debug('Found subtitle via hash search')
                        return [
                            SubtisSubtitle(
                                language=language,
                                subtitle_id=subtitle_link,
                                page_link=hash_url,
                                title=title_name,
                                download_link=subtitle_link,
                                is_synced=True,
                                video_hash=video_hash,
                            )
                        ]

        if video.size:
            bytes_url = f'{self.server_url}/subtitle/find/file/bytes/{video.size}'
            logger.info('Searching subtitles by bytes for %s', filename)
            data = self._session_request(bytes_url)
            if data:
                parsed = self._parse_response(data)
                if parsed:
                    subtitle_link, title_name = parsed
                    logger.debug('Found subtitle via bytes search')
                    return [
                        SubtisSubtitle(
                            language=language,
                            subtitle_id=subtitle_link,
                            page_link=bytes_url,
                            title=title_name,
                            download_link=subtitle_link,
                            is_synced=True,
                        )
                    ]

        filename_url = f'{self.server_url}/subtitle/find/file/name/{encoded_filename}'
        logger.info('Searching subtitles by filename for %s', filename)
        data = self._session_request(filename_url)
        if data:
            parsed = self._parse_response(data)
            if parsed:
                subtitle_link, title_name = parsed
                logger.debug('Found subtitle via filename search')
                return [
                    SubtisSubtitle(
                        language=language,
                        subtitle_id=subtitle_link,
                        page_link=filename_url,
                        title=title_name,
                        download_link=subtitle_link,
                        is_synced=True,
                    )
                ]

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
