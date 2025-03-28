"""Provider for NapiProjekt."""

from __future__ import annotations

import hashlib
import io
import logging
from gzip import BadGzipFile, GzipFile
from typing import TYPE_CHECKING, ClassVar

from babelfish import Language  # type: ignore[import-untyped]
from requests import Session

from subliminal.exceptions import NotInitializedProviderError
from subliminal.subtitle import Subtitle, fix_line_ending

from . import Provider

if TYPE_CHECKING:
    import os
    from collections.abc import Set

    from subliminal.video import Video

logger = logging.getLogger(__name__)


def get_subhash(video_hash: str) -> str:
    """Get a second hash based on napiprojekt's hash.

    :param str video_hash: napiprojekt's hash.
    :return: the subhash.
    :rtype: str

    """
    idx = [0xE, 0x3, 0x6, 0x8, 0x2]
    mul = [2, 2, 5, 4, 3]
    add = [0, 0xD, 0x10, 0xB, 0x5]

    b = []
    for i in range(len(idx)):
        a = add[i]
        m = mul[i]
        i = idx[i]
        t = a + int(video_hash[i], 16)
        v = int(video_hash[t : t + 2], 16)
        b.append(('%x' % (v * m))[-1])

    return ''.join(b)


class NapiProjektSubtitle(Subtitle):
    """NapiProjekt Subtitle."""

    provider_name: ClassVar[str] = 'napiprojekt'

    video_hash: str

    def __init__(
        self,
        language: Language,
        subtitle_id: str,
        *,
        fps: float = 24,
    ) -> None:
        super().__init__(language, subtitle_id, fps=fps)

    @property
    def info(self) -> str:
        """Information about the subtitle."""
        return str(self.subtitle_id)

    def get_matches(self, video: Video) -> set[str]:
        """Get the matches against the `video`."""
        matches = set()

        # video_hash
        if 'napiprojekt' in video.hashes and video.hashes['napiprojekt'] == self.subtitle_id:
            matches.add('hash')

        return matches


class NapiProjektProvider(Provider):
    """NapiProjekt Provider."""

    languages: ClassVar[Set[Language]] = {Language.fromalpha2(lang) for lang in ['pl']}
    subtitle_class: ClassVar = NapiProjektSubtitle

    required_hash: ClassVar = 'napiprojekt'
    server_url: ClassVar[str] = 'https://napiprojekt.pl/unit_napisy/dl.php'

    timeout: int
    session: Session | None

    def __init__(self, *, timeout: int = 10) -> None:
        self.timeout = timeout
        self.session = None

    @staticmethod
    def hash_video(video_path: str | os.PathLike) -> str | None:
        """Compute a hash using NapiProjekt's algorithm.

        :param str video_path: path of the video.
        :return: the hash.
        :rtype: str

        """
        readsize = 1024 * 1024 * 10
        with open(video_path, 'rb') as f:
            data = f.read(readsize)
        return hashlib.md5(data).hexdigest()  # noqa: S324

    def initialize(self) -> None:
        """Initialize the provider."""
        self.session = Session()
        self.session.headers['User-Agent'] = self.user_agent

    def terminate(self) -> None:
        """Terminate the provider."""
        if self.session is None:
            raise NotInitializedProviderError
        self.session.close()

    def _parse_content(self, content: bytes) -> bytes:
        """Parse the subtitle content from the response."""
        gzip_prefix = b'\x1f\x8b\x08'

        # GZipped file
        if content.startswith(gzip_prefix):
            # open the zip
            try:
                with GzipFile(fileobj=io.BytesIO(content)) as gz:
                    content = gz.read()

            except BadGzipFile:
                return b''

        # Handle subtitles not found and errors
        if content[:4] == b'NPc0':
            return b''
        return fix_line_ending(content)

    def query(self, language: Language, video_hash: str) -> list[NapiProjektSubtitle]:
        """Query the provider for subtitles.

        :param :class:`~babelfish.language.Language` language: the language of the subtitles.
        :param int video_hash: the hash of the video.

        :return: the list of found subtitles.
        :rtype: list[NapiProjektSubtitle]

        """
        if self.session is None:
            raise NotInitializedProviderError

        params = {
            'v': 'dreambox',
            'kolejka': 'false',
            'nick': '',
            'pass': '',
            'napios': 'Linux',
            'l': language.alpha2.upper(),
            'f': video_hash,
            't': get_subhash(video_hash),
        }
        logger.info('Searching subtitle %r', params)
        r = self.session.get(self.server_url, params=params, timeout=self.timeout)
        r.raise_for_status()

        # Parse content
        content = self._parse_content(r.content)
        if not content:
            logger.debug('No subtitles found')
            return []

        # Create subtitle object
        subtitle = self.subtitle_class(language=language, subtitle_id=video_hash)
        subtitle.set_content(content)
        logger.debug('Found subtitle %r', subtitle)

        return [subtitle]

    def list_subtitles(self, video: Video, languages: Set[Language]) -> list[NapiProjektSubtitle]:
        """List all the subtitles for the video."""
        return [s[0] for s in [self.query(lang, video.hashes['napiprojekt']) for lang in languages] if len(s) > 0]

    def download_subtitle(self, subtitle: NapiProjektSubtitle) -> None:
        """Download the content of the subtitle."""
        # there is no download step, content is already filled from listing subtitles
        return
