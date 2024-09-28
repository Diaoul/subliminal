"""Mock provider, for testing purposes."""

from __future__ import annotations

import logging
from importlib import import_module
from itertools import count
from typing import TYPE_CHECKING, Any, ClassVar

from babelfish import LANGUAGES, Language  # type: ignore[import-untyped]

from subliminal.exceptions import NotInitializedProviderError
from subliminal.matches import guess_matches
from subliminal.subtitle import Subtitle
from subliminal.video import Episode, Movie, Video

from . import Provider

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence, Set

logger = logging.getLogger(__name__)


class MockSubtitle(Subtitle):
    """Mock Subtitle."""

    provider_name: ClassVar[str] = 'mock'
    _ids: ClassVar = count(0)

    fake_content: bytes
    video_name: str
    matches: set[str]
    force_matches: bool

    def __init__(
        self,
        language: Language,
        *,
        subtitle_id: str = '',
        fake_content: bytes = b'',
        video_name: str = '',
        matches: Set[str] | None = None,
        parameters: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        # generate unique id for mock subtitle
        next_id: int = next(self._ids)
        if not subtitle_id:
            subtitle_id = f'S{next_id:05d}'
        super().__init__(
            language,
            subtitle_id,
            **kwargs,
        )
        self.fake_content = fake_content
        self.video_name = video_name
        self.force_matches = matches is not None
        self.matches = set(matches) if matches is not None else set()
        self.parameters = dict(parameters) if parameters is not None else {}

    def get_matches(self, video: Video) -> set[str]:
        """Get the matches against the `video`."""
        if self.force_matches:
            return self.matches
        return guess_matches(video, self.parameters)


class MockProvider(Provider):
    """Mock Provider."""

    languages: ClassVar[Set[Language]] = {Language(lang) for lang in LANGUAGES}
    subtitle_class: ClassVar = MockSubtitle
    internal_subtitle_pool: ClassVar[list[MockSubtitle]] = []

    video_types: ClassVar = (Episode, Movie)

    logged_in: bool
    subtitle_pool: list[MockSubtitle]

    def __init__(self, subtitle_pool: Sequence[MockSubtitle] | None = None) -> None:
        self.logged_in = False
        self.subtitle_pool = list(self.internal_subtitle_pool)
        if subtitle_pool is not None:
            self.subtitle_pool.extend(list(subtitle_pool))

    def initialize(self) -> None:
        """Initialize the provider."""
        self.logged_in = True

    def terminate(self) -> None:
        """Terminate the provider."""
        if not self.logged_in:
            raise NotInitializedProviderError

        self.logged_in = False

    def query(
        self,
        languages: Set[Language],
        video: Video | None = None,
        matches: Set[str] | None = None,
    ) -> list[MockSubtitle]:
        """Query the provider for subtitles."""
        subtitles = []
        for lang in languages:
            subtitle = MockSubtitle(language=lang, video=video, matches=matches)
            subtitles.append(subtitle)
        return subtitles

    def list_subtitles(self, video: Video, languages: Set[Language]) -> list[MockSubtitle]:
        """List all the subtitles for the video."""
        return [
            subtitle
            for subtitle in self.subtitle_pool
            if subtitle.language in languages and subtitle.video_name == video.name
        ]

    def download_subtitle(self, subtitle: MockSubtitle) -> None:
        """Download the content of the subtitle."""
        subtitle.content = subtitle.fake_content


def mock_subtitle_provider(name: str, subtitles_info: Sequence[Mapping[str, Any]]) -> str:
    """Mock a subtitle provider, providing subtitles."""
    name_lower = name.lower()
    subtitle_class_name = f'{name}Subtitle'
    provider_class_name = f'{name}Provider'

    # MockSubtitle subclass
    MyMockSubtitle = type(subtitle_class_name, (MockSubtitle,), {'provider_name': name_lower})

    subtitle_pool = [MyMockSubtitle(**kw) for kw in subtitles_info]

    MyMockProvider = type(
        provider_class_name,
        (MockProvider,),
        {
            'subtitle_class': MyMockSubtitle,
            'internal_subtitle_pool': subtitle_pool,
        },
    )

    mod = import_module('subliminal.providers.mock')
    setattr(mod, provider_class_name, MyMockProvider)

    return f'{name_lower} = subliminal.providers.mock:{provider_class_name}'
